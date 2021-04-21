#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# this file is modified from https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking/blob/master/Metrica_PitchControl.py
# original author: Laurie Shaw (research work developed by William Spearman)

"""
Created on Mon Apr 19 14:52:19 2020

Module for calculating a Pitch Control surface using MetricaSports's tracking & event data.

Pitch control (at a given location on the field) is the probability that a team will gain 
possession if the ball is moved to that location on the field. 

Methdology is described in "Off the ball scoring opportunities" by William Spearman:
http://www.sloansportsconference.com/wp-content/uploads/2018/02/2002.pdf

GitHub repo for this code can be found here:
https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking

Data can be found at: https://github.com/metrica-sports/sample-data

Functions
----------

calculate_pitch_control_at_target(): calculate the pitch control probability for the attacking and defending teams at a specified target position on the ball.

generate_pitch_control_for_event(): this function evaluates pitch control surface over the entire field at the moment
of the given event (determined by the index of the event passed as an input)

Classes
---------

The 'player' class collects and stores trajectory information for each player required by the pitch control calculations.

@author: Laurie Shaw (@EightyFivePoint)

Modified for pitchly by @author: Vinay Warrier (@opunsoars)

"""

import numpy as np


def initialise_players(frame_data, params):
    """
    initialise_players(team,teamname,params)

    create a list of player objects that holds their positions and velocities from the tracking data dataframe

    Parameters
    -----------

    team: row (i.e. instant) of either the home or away team tracking Dataframe
    teamname: team name "Home" or "Away"
    params: Dictionary of model parameters (default model parameters can be generated using default_model_params() )

    Returns
    -----------

    team_players: list of player objects for the team at at given instant

    """
    # get player  ids
    player_ids = np.unique([x.split("_")[0] for x in frame_data.keys()])
    # create list
    team_players = []
    for p in player_ids:
        # create a player object for player_id 'p'
        team_player = player(p, frame_data, params)
        if team_player.inframe:
            team_players.append(team_player)
    return team_players


class player(object):
    """
    player() class

    Class defining a player object that stores position, velocity, time-to-intercept and pitch control contributions for a player

    __init__ Parameters
    -----------
    pid: id (jersey number) of player
    team: row of tracking data for team
    teamname: team name "Home" or "Away"
    params: Dictionary of model parameters (default model parameters can be generated using default_model_params() )


    methods include:
    -----------
    simple_time_to_intercept(r_final): time take for player to get to target position (r_final) given current position
    probability_intercept_ball(T): probability player will have controlled ball at time T given their expected time_to_intercept

    """

    # player object holds position, velocity, time-to-intercept and pitch control contributions for each player

    def __init__(self, pid, frame_data, params):
        self.id = pid
        # player max speed in m/s. Could be individualised
        self.vmax = params["max_player_speed"]
        # player reaction time in 's'. Could be individualised
        self.reaction_time = params["reaction_time"]
        # standard deviation of sigmoid function (see Eq 4 in Spearman, 2018)
        self.tti_sigma = params["tti_sigma"]
        self.get_position(frame_data)
        self.get_velocity(frame_data)
        self.PPCF = 0.0  # initialise this for later

    def get_position(self, frame_data):
        self.position = np.array([frame_data[f"{self.id}_x"], frame_data[f"{self.id}_y"]])
        self.inframe = not np.any(np.isnan(self.position))

    def get_velocity(self, frame_data):
        self.velocity = np.array([frame_data[f"{self.id}_vx"], frame_data[f"{self.id}_vy"]])
        if np.any(np.isnan(self.velocity)):
            self.velocity = np.array([0.0, 0.0])

    def simple_time_to_intercept(self, r_final):
        self.PPCF = 0.0  # initialise this for later
        # Time to intercept assumes that the player continues moving at current velocity for 'reaction_time' seconds
        # and then runs at full speed to the target position.
        r_reaction = self.position + self.velocity * self.reaction_time
        self.time_to_intercept = self.reaction_time + np.linalg.norm(r_final - r_reaction) / self.vmax
        return self.time_to_intercept

    def probability_intercept_ball(self, T):
        # probability of a player arriving at target location at time 'T' given their expected time_to_intercept (time of arrival), as described in Spearman 2018
        f = 1 / (1.0 + np.exp(-np.pi / np.sqrt(3.0) / self.tti_sigma * (T - self.time_to_intercept)))
        return f


""" Generate pitch control map """


def default_model_params(time_to_control_veto=3):
    """
    default_model_params()

    Returns the default parameters that define and evaluate the model. See Spearman 2018 for more details.

    Parameters
    -----------
    time_to_control_veto: If the probability that another team or player can get to the ball and control it is less than 10^-time_to_control_veto, ignore that player.


    Returns
    -----------

    params: dictionary of parameters required to determine and calculate the model

    """
    # key parameters for the model, as described in Spearman 2018
    params = {}
    # model parameters
    params["max_player_accel"] = 7.0  # maximum player acceleration m/s/s, not used in this implementation
    params["max_player_speed"] = 5.0  # maximum player speed m/s
    # seconds, time taken for player to react and change trajectory. Roughly determined as vmax/amax
    params["reaction_time"] = 0.7
    # Standard deviation of sigmoid function in Spearman 2018 ('s') that determines uncertainty in player arrival time
    params["tti_sigma"] = 0.45
    # kappa parameter in Spearman 2018 (=1.72 in the paper) that gives the advantage defending players to control ball, I have set to 1 so that home & away players have same ball control probability
    params["kappa_def"] = 1.0
    params["lambda_att"] = 4.3  # ball control parameter for attacking team
    # ball control parameter for defending team
    params["lambda_def"] = 4.3 * params["kappa_def"]
    params["average_ball_speed"] = 15.0  # average ball travel speed in m/s
    # numerical parameters for model evaluation
    params["int_dt"] = 0.04  # integration timestep (dt)
    params["max_int_time"] = 10  # upper limit on integral time
    # assume convergence when PPCF>0.99 at a given location.
    params["model_converge_tol"] = 0.01
    # The following are 'short-cut' parameters. We do not need to calculated PPCF explicitly when a player has a sufficient head start.
    # A sufficient head start is when the a player arrives at the target location at least 'time_to_control' seconds before the next player
    params["time_to_control_att"] = (
        time_to_control_veto * np.log(10) * (np.sqrt(3) * params["tti_sigma"] / np.pi + 1 / params["lambda_att"])
    )
    params["time_to_control_def"] = (
        time_to_control_veto * np.log(10) * (np.sqrt(3) * params["tti_sigma"] / np.pi + 1 / params["lambda_def"])
    )
    return params


def generate_pitch_control_for_event(
    event_id,
    events,
    tracking_home,
    tracking_away,
    params,
    field_dimen=(106.0, 68.0),
    n_grid_cells_x=50,
):
    """generate_pitch_control_for_event

    Evaluates pitch control surface over the entire field at the moment of the given event (determined by the index of the event passed as an input)

    Parameters
    -----------
        event_id: Index (not row) of the event that describes the instant at which the pitch control surface should be calculated
        events: Dataframe containing the event data
        tracking_home: tracking DataFrame for the Home team
        tracking_away: tracking DataFrame for the Away team
        params: Dictionary of model parameters (default model parameters can be generated using default_model_params() )
        field_dimen: tuple containing the length and width of the pitch in meters. Default is (106,68)
        n_grid_cells_x: Number of pixels in the grid (in the x-direction) that covers the surface. Default is 50.
                        n_grid_cells_y will be calculated based on n_grid_cells_x and the field dimensions

    Returrns
    -----------
        PPCFa: Pitch control surface (dimen (n_grid_cells_x,n_grid_cells_y) ) containing pitch control probability for the attcking team.
               Surface for the defending team is just 1-PPCFa.
        xgrid: Positions of the pixels in the x-direction (field length)
        ygrid: Positions of the pixels in the y-direction (field width)

    """
    # get the details of the event (frame, team in possession, ball_start_position)
    pass_frame = events.loc[event_id]["Start Frame"]
    pass_team = events.loc[event_id].Team
    # print(pass_team)
    ball_start_pos = np.array([events.loc[event_id]["Start X"], events.loc[event_id]["Start Y"]])
    # break the pitch down into a grid
    n_grid_cells_y = int(n_grid_cells_x * field_dimen[1] / field_dimen[0])
    xgrid = np.linspace(-field_dimen[0] / 2.0, field_dimen[0] / 2.0, n_grid_cells_x)
    ygrid = np.linspace(-field_dimen[1] / 2.0, field_dimen[1] / 2.0, n_grid_cells_y)
    # initialise pitch control grids for attacking and defending teams
    PPCFa = np.zeros(shape=(len(ygrid), len(xgrid)))
    PPCFd = np.zeros(shape=(len(ygrid), len(xgrid)))
    # initialise player positions and velocities for pitch control calc (so that we're not repeating this at each grid cell position)
    if pass_team == "Home":
        attacking_players = initialise_players(tracking_home.loc[pass_frame], "Home", params)
        defending_players = initialise_players(tracking_away.loc[pass_frame], "Away", params)
    elif pass_team == "Away":
        defending_players = initialise_players(tracking_home.loc[pass_frame], "Home", params)
        attacking_players = initialise_players(tracking_away.loc[pass_frame], "Away", params)
    else:
        assert False, "Team in possession must be either home or away"
    # calculate pitch pitch control model at each location on the pitch
    for i in range(len(ygrid)):
        for j in range(len(xgrid)):
            target_position = np.array([xgrid[j], ygrid[i]])
            PPCFa[i, j], PPCFd[i, j] = calculate_pitch_control_at_target(
                target_position, attacking_players, defending_players, ball_start_pos, params
            )
    # check probabilitiy sums within convergence
    checksum = np.sum(PPCFa + PPCFd) / float(n_grid_cells_y * n_grid_cells_x)
    assert 1 - checksum < params["model_converge_tol"], "Checksum failed: %1.3f" % (1 - checksum)
    return PPCFa, xgrid, ygrid


def calculate_pitch_control_at_target(
    target_position,
    attacking_players,
    defending_players,
    ball_start_pos,
    params=default_model_params(),
    return_individual=False,
):
    """calculate_pitch_control_at_target

    Calculates the pitch control probability for the attacking and defending teams at a specified target position on the ball.

    Parameters
    -----------
        target_position: size 2 numpy array containing the (x,y) position of the position on the field to evaluate pitch control
        attacking_players: list of 'player' objects (see player class above) for the players on the attacking team (team in possession)
        defending_players: list of 'player' objects (see player class above) for the players on the defending team
        ball_start_pos: Current position of the ball (start position for a pass). If set to NaN, function will assume that the ball is already at the target position.
        params: Dictionary of model parameters (default model parameters can be generated using default_model_params() )

    Returrns
    -----------
        PPCFatt: Pitch control probability for the attacking team
        PPCFdef: Pitch control probability for the defending team ( 1-PPCFatt-PPCFdef <  params['model_converge_tol'] )

    """
    # calculate ball travel time from start position to end position.
    # assume that ball is already at location
    if ball_start_pos is None or any(np.isnan(ball_start_pos)):
        ball_travel_time = 0.0
    else:
        # ball travel time is distance to target position from current ball position divided assumed average ball speed
        ball_travel_time = np.linalg.norm(target_position - ball_start_pos) / params["average_ball_speed"]

    # first get arrival time of 'nearest' attacking player (nearest also dependent on current velocity)
    tau_min_att = np.nanmin([p.simple_time_to_intercept(target_position) for p in attacking_players])
    tau_min_def = np.nanmin([p.simple_time_to_intercept(target_position) for p in defending_players])

    # check whether we actually need to solve equation 3
    if tau_min_att - max(ball_travel_time, tau_min_def) >= params["time_to_control_def"]:
        # if defending team can arrive significantly before attacking team, no need to solve pitch control model
        return 0.0, 1.0
    elif tau_min_def - max(ball_travel_time, tau_min_att) >= params["time_to_control_att"]:
        # if attacking team can arrive significantly before defending team, no need to solve pitch control model
        return 1.0, 0.0
    else:
        # solve pitch control model by integrating equation 3 in Spearman et al.
        # first remove any player that is far (in time) from the target location
        attacking_players = [
            p for p in attacking_players if p.time_to_intercept - tau_min_att < params["time_to_control_att"]
        ]
        defending_players = [
            p for p in defending_players if p.time_to_intercept - tau_min_def < params["time_to_control_def"]
        ]
        # set up integration arrays
        dT_array = np.arange(
            ball_travel_time - params["int_dt"], ball_travel_time + params["max_int_time"], params["int_dt"]
        )
        PPCFatt = np.zeros_like(dT_array)
        PPCFdef = np.zeros_like(dT_array)
        # integration equation 3 of Spearman 2018 until convergence or tolerance limit hit (see 'params')
        ptot = 0.0
        i = 1
        Patt = {}
        Pdef = {}
        while 1 - ptot > params["model_converge_tol"] and i < dT_array.size:
            T = dT_array[i]
            for player in attacking_players:
                # calculate ball control probablity for 'player' in time interval T+dt
                dPPCFdT = (
                    (1 - PPCFatt[i - 1] - PPCFdef[i - 1]) * player.probability_intercept_ball(T) * params["lambda_att"]
                )
                # make sure it's greater than zero
                assert dPPCFdT >= 0, "Invalid attacking player probability (calculate_pitch_control_at_target)"
                # total contribution from individual player
                player.PPCF += dPPCFdT * params["int_dt"]
                # add to sum over players in the attacking team (remembering array element is zero at the start of each integration iteration)
                PPCFatt[i] += player.PPCF
                Patt[player.id] = player.PPCF
            for player in defending_players:
                # calculate ball control probablity for 'player' in time interval T+dt
                dPPCFdT = (
                    (1 - PPCFatt[i - 1] - PPCFdef[i - 1]) * player.probability_intercept_ball(T) * params["lambda_def"]
                )
                # make sure it's greater than zero
                assert dPPCFdT >= 0, "Invalid defending player probability (calculate_pitch_control_at_target)"
                # total contribution from individual player
                player.PPCF += dPPCFdT * params["int_dt"]
                # add to sum over players in the defending team
                PPCFdef[i] += player.PPCF
                Pdef[player.id] = player.PPCF
            ptot = PPCFdef[i] + PPCFatt[i]  # total pitch control probability
            i += 1
        if i >= dT_array.size:
            print("Integration failed to converge: %1.3f" % (ptot))

        if return_individual == True:

            return PPCFatt[i - 1], PPCFdef[i - 1], Patt, Pdef
        else:
            return PPCFatt[i - 1], PPCFdef[i - 1]


def generate_pitch_control_for_frame(
    frame_data,
    home_cols,
    away_cols,
    params=default_model_params(),
    attacking="Home",
    field_dimen=(
        106.0,
        68.0,
    ),
    n_grid_cells_x=50,
    return_individual=False,
):
    """generate_pitch_control_for_frame

    Evaluates pitch control surface over the entire field at the moment of the given event (determined by the index of the event passed as an input)

    Parameters
    -----------
        event_id: Index (not row) of the event that describes the instant at which the pitch control surface should be calculated
        events: Dataframe containing the event data
        tracking_home: tracking DataFrame for the Home team
        tracking_away: tracking DataFrame for the Away team
        params: Dictionary of model parameters (default model parameters can be generated using default_model_params() )
        field_dimen: tuple containing the length and width of the pitch in meters. Default is (106,68)
        n_grid_cells_x: Number of pixels in the grid (in the x-direction) that covers the surface. Default is 50.
                        n_grid_cells_y will be calculated based on n_grid_cells_x and the field dimensions

    Returrns
    -----------
        PPCFa: Pitch control surface (dimen (n_grid_cells_x,n_grid_cells_y) ) containing pitch control probability for the attcking team.
               Surface for the defending team is just 1-PPCFa.
        xgrid: Positions of the pixels in the x-direction (field length)
        ygrid: Positions of the pixels in the y-direction (field width)

    """

    # get the details of the frame: team in possession, ball_start_position)
    ball_start_pos = frame_data[["ball_x", "ball_y"]].to_list()

    # break the pitch down into a grid
    n_grid_cells_y = int(n_grid_cells_x * field_dimen[1] / field_dimen[0])
    xgrid = np.linspace(-field_dimen[0] / 2.0, field_dimen[0] / 2.0, n_grid_cells_x)
    ygrid = np.linspace(-field_dimen[1] / 2.0, field_dimen[1] / 2.0, n_grid_cells_y)

    # initialise pitch control grids for attacking and defending teams
    PPCFa = np.zeros(shape=(len(ygrid), len(xgrid)))
    PPCFd = np.zeros(shape=(len(ygrid), len(xgrid)))

    # pick only the columns representing players whose data is available for this match
    # Basically playerIDs that have data for this row/frame
    homeplayers = [x.split("_")[0] for x in frame_data[[c for c in home_cols if c.endswith("_x")]].dropna().keys()]
    awayplayers = [x.split("_")[0] for x in frame_data[[c for c in away_cols if c.endswith("_x")]].dropna().keys()]

    # initialise pitch control grids for individual players in attacking and defending teams
    PPCFa_pax = {pid: np.zeros(shape=(len(ygrid), len(xgrid))) for pid in homeplayers}
    PPCFd_pax = {pid: np.zeros(shape=(len(ygrid), len(xgrid))) for pid in awayplayers}

    # initialise player positions and velocities for pitch control calc (so that we're not repeating this at each grid cell position)
    if attacking == "Home":
        attacking_players = initialise_players(frame_data[home_cols], params)
        defending_players = initialise_players(frame_data[away_cols], params)
        opp = "Away"
    elif attacking == "Away":
        defending_players = initialise_players(frame_data[home_cols], params)
        attacking_players = initialise_players(frame_data[away_cols], params)
        opp = "Home"
    else:
        assert False, "Team in possession must be either home or away"

    # calculate pitch pitch control model at each location on the pitch
    for i in range(len(ygrid)):
        for j in range(len(xgrid)):
            target_position = np.array([xgrid[j], ygrid[i]])
            if return_individual == True:
                # print (target_position)
                out = calculate_pitch_control_at_target(
                    target_position,
                    attacking_players,
                    defending_players,
                    ball_start_pos,
                    params,
                    return_individual=True,
                )
                if len(out) < 4:
                    PPCFa[i, j], PPCFd[i, j] = out

                else:

                    # print (target_position, out, [type(x) for x in out])
                    PPCFa[i, j], PPCFd[i, j], Patt, Pdef = out

                    for pid, ppcf_pax in Patt.items():
                        PPCFa_pax[pid][i, j] = ppcf_pax

                    for pid, ppcf_pax in Pdef.items():
                        PPCFd_pax[pid][i, j] = ppcf_pax
            else:
                PPCFa[i, j], PPCFd[i, j] = calculate_pitch_control_at_target(
                    target_position, attacking_players, defending_players, ball_start_pos, params
                )

    # check probabilitiy sums within convergence
    checksum = np.sum(PPCFa + PPCFd) / float(n_grid_cells_y * n_grid_cells_x)
    assert 1 - checksum < params["model_converge_tol"], "Checksum failed: %1.3f" % (1 - checksum)

    pitch_control_dict = dict()
    if return_individual == True:
        pitch_control_dict["PPCFa"] = PPCFa
        pitch_control_dict["xgrid"] = xgrid
        pitch_control_dict["ygrid"] = ygrid
        pitch_control_dict["PPCFa_pax"] = PPCFa_pax
        return pitch_control_dict
    else:
        pitch_control_dict["PPCFa"] = PPCFa
        pitch_control_dict["xgrid"] = xgrid
        pitch_control_dict["ygrid"] = ygrid
        return pitch_control_dict
