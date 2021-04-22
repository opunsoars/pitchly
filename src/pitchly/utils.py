import glob

import numpy as np
import pandas as pd
import scipy.signal as signal

from .params import prm

match_dir = "/media/opunsoars/My Book/playground/friends_of_tracking/friends_of_tracking/\
    datahub/metrica_sports/sample-data/data/Sample_Game_1"


def modify_cols(tracking_df):
    cols = list(tracking_df.iloc[2, :3])
    # cols = cols[:3]
    for i in range(3, tracking_df.shape[1] - 2, 2):
        cols.append(f"{tracking_df.iloc[0,i]}_{tracking_df.iloc[1,i]}_X")
        cols.append(f"{tracking_df.iloc[0,i]}_{tracking_df.iloc[1,i]}_Y")
    cols.append("ball_X")
    cols.append("ball_Y")

    tracking_df.columns = cols
    tracking_df = tracking_df.loc[3:, :]
    for col in cols[2:]:
        tracking_df[col] = tracking_df[col].astype(float)
    tracking_df["Frame"] = tracking_df.Frame.astype(int)
    tracking_df["Period"] = tracking_df.Period.astype(int)
    tracking_df["mins"] = tracking_df["Time [s]"].apply(
        lambda x: f"{x//60:0.0f}:{x%60:0.2f}"
    )
    tracking_df.set_index("Frame", inplace=True)
    return tracking_df


def convert_to_metric_coords(data, field_dimen=prm.field_dim):
    """
    Convert positions from Metrica units to meters (with origin at centre circle)
    """
    x_columns = [c for c in data.columns if c.endswith("X")]
    y_columns = [c for c in data.columns if c.endswith("Y")]
    data[x_columns] = (data[x_columns] - 0.5) * field_dimen[0]
    data[y_columns] = -1 * (data[y_columns] - 0.5) * field_dimen[1]
    """
    ------------ ***NOTE*** ------------
    Metrica actually define the origin at the *top*-left of the field, not the bottom-left, as discussed in the YouTube video.
    I've changed the line above to reflect this. It was originally:
    data[y_columns] = ( data[y_columns]-0.5 ) * field_dimen[1]
    ------------ ********** ------------
    """
    return data


def calc_player_velocities(
    team,
    smoothing=True,
    filter_="moving average",
    window=7,
    polyorder=1,
    maxspeed=12,
):
    """calc_player_velocities( tracking_data )

    Calculate player velocities in x & y direciton, and total player speed at each timestamp of the tracking data

    Parameters
    -----------
        team: the tracking DataFrame for home or away team
        smoothing: boolean variable that determines whether velocity measures are smoothed. Default is True.
        filter: type of filter to use when smoothing the velocities. Default is Savitzky-Golay,\
             which fits a polynomial of order 'polyorder' to the data within each window
        window: smoothing window size in # of frames
        polyorder: order of the polynomial for the Savitzky-Golay filter. \
            Default is 1 - a linear fit to the velcoity, so gradient is the acceleration
        maxspeed: the maximum speed that a player can realisitically achieve (in meters/second). \
            d measures that exceed maxspeed are tagged as outliers and set to NaN.

    Returrns
    -----------
       team : the tracking DataFrame with columns for speed in the x & y direction and total speed added

    """
    # remove any velocity data already in the dataframe
    team = remove_player_velocities(team)
    # print (team.isna().sum())

    # Get the player ids
    player_ids = np.unique(
        [c[:-2] for c in team.columns if c[:4] in ["Home", "Away"]]
    )

    # Calculate the timestep from one frame to the next. Should always be 0.04 within the same half
    dt = team["Time [s]"].diff()

    # index of first frame in second half
    second_half_idx = team.Period.idxmax(2)

    # estimate velocities for players in team
    for player in player_ids:  # cycle through players individually
        # difference player positions in timestep dt to get unsmoothed estimate of velicity
        vx = team[player + "_X"].diff() / dt
        vy = team[player + "_Y"].diff() / dt

        if maxspeed > 0:
            # remove unsmoothed data points that exceed the maximum speed (these are most likely position errors)
            raw_speed = np.sqrt(vx ** 2 + vy ** 2)
            vx[raw_speed > maxspeed] = np.nan
            vy[raw_speed > maxspeed] = np.nan

        if smoothing:
            if filter_ == "Savitzky-Golay":
                # calculate first half velocity
                vx.iloc[:second_half_idx] = signal.savgol_filter(
                    vx.iloc[:second_half_idx],
                    window_length=window,
                    polyorder=polyorder,
                )
                vy.iloc[:second_half_idx] = signal.savgol_filter(
                    vy.iloc[:second_half_idx],
                    window_length=window,
                    polyorder=polyorder,
                )
                # calculate second half velocity
                vx.iloc[second_half_idx:] = signal.savgol_filter(
                    vx.iloc[second_half_idx:],
                    window_length=window,
                    polyorder=polyorder,
                )
                vy.iloc[second_half_idx:] = signal.savgol_filter(
                    vy.iloc[second_half_idx:],
                    window_length=window,
                    polyorder=polyorder,
                )
            elif filter_ == "moving average":
                ma_window = np.ones(window) / window
                # calculate first half velocity
                vx.iloc[:second_half_idx] = np.convolve(
                    vx.iloc[:second_half_idx], ma_window, mode="same"
                )
                vy.iloc[:second_half_idx] = np.convolve(
                    vy.iloc[:second_half_idx], ma_window, mode="same"
                )
                # calculate second half velocity
                vx.iloc[second_half_idx:] = np.convolve(
                    vx.iloc[second_half_idx:], ma_window, mode="same"
                )
                vy.iloc[second_half_idx:] = np.convolve(
                    vy.iloc[second_half_idx:], ma_window, mode="same"
                )

        # put player speed in x,y direction, and total speed back in the data frame
        team[player + "_vx"] = vx
        team[player + "_vy"] = vy
        team[player + "_speed"] = np.sqrt(vx ** 2 + vy ** 2)

    return team


def remove_player_velocities(team):
    # remove player velocoties and acceleeration measures that are already in the 'team' dataframe
    columns = [
        c
        for c in team.columns
        if c.split("_")[-1] in ["vx", "vy", "ax", "ay", "speed", "acceleration"]
    ]  # Get the player ids
    team = team.drop(columns=columns)
    return team


def flip_second_half_direction(team):
    """
    Flip coordinates in second half so that each team always shoots in the same direction through the match.
    """
    second_half_idx = team.Period.idxmax(2)
    columns = [c for c in team.columns if c[-1].lower() in ["x", "y"]]
    team.loc[second_half_idx:, columns] *= -1
    return team


def load_data(match_dir):

    home_track = (
        pd.read_csv(glob.glob(f"{match_dir}/*Home*.csv")[0], header=None)
        .pipe(modify_cols)
        .pipe(convert_to_metric_coords)
        .pipe(calc_player_velocities)
        .pipe(flip_second_half_direction)
    )

    away_track = (
        pd.read_csv(glob.glob(f"{match_dir}/*Away*.csv")[0], header=None)
        .pipe(modify_cols)
        .pipe(convert_to_metric_coords)
        .pipe(calc_player_velocities)
        .pipe(flip_second_half_direction)
    )

    events = (
        pd.read_csv(glob.glob(f"{match_dir}/*Events*.csv")[0])
        .pipe(convert_to_metric_coords)
        .pipe(flip_second_half_direction)
    )

    return home_track, away_track, events


# tracking_home, tracking_away, events = load_data(match_dir)
