import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go
from scipy import signal
from tqdm.auto import tqdm

from .params import prm
from .pitch import Pitch
from .pitch_control import generate_pitch_control_for_frame


class TrackingData:
    def __init__(self, data, metadata):
        self.metadata = metadata
        self.home_players = [
            x.player_id for x in self.metadata.teams[0].players
        ]
        self.away_players = [
            x.player_id for x in self.metadata.teams[1].players
        ]
        self.home_jerseys = [
            x.jersey_no for x in self.metadata.teams[0].players
        ]
        self.away_jerseys = [
            x.jersey_no for x in self.metadata.teams[1].players
        ]

        data = self.metric_coords(data)
        data = self.flip_direction(data, period=1)
        data = self.calc_player_velocities(data, filter_="moving average")
        self.data = data

    def metric_coords(self, data, field_dimen=prm.field_dim):
        x_columns = [c for c in data.columns if c.endswith("_x")]
        y_columns = [c for c in data.columns if c.endswith("_y")]
        data[x_columns] = (data[x_columns] - 0.5) * field_dimen[0]
        data[y_columns] = -1 * (data[y_columns] - 0.5) * field_dimen[1]

        return data

    def calc_player_velocities(
        self,
        data,
        smoothing=True,
        filter_="moving average",
        window=7,
        polyorder=1,
        maxspeed=12,
    ):
        # Get the player ids
        player_ids = self.home_players + self.away_players
        # Calculate the timestep from one frame to the next.
        # Should always be 0.04 within the same half
        dt = data.timestamp.diff()

        # index of first frame in second half
        second_half_idx = data.period_id.idxmax(2)
        # estimate velocities for players in team
        for player in player_ids:  # cycle through players individually
            # difference player positions in timestep dt to get unsmoothed
            # estimate of velicity
            vx = data[player + "_x"].diff() / dt
            vy = data[player + "_y"].diff() / dt

            if maxspeed > 0:
                # remove unsmoothed data points that exceed the maximum speed
                # (these are most likely position errors)
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

            # put player speed in x,y direction, and total speed back in the
            # data frame
            data[player + "_vx"] = vx
            data[player + "_vy"] = vy
            data[player + "_speed"] = np.sqrt(vx ** 2 + vy ** 2)

        return data

    def flip_direction(self, data, period=2):
        """
        Flip coordinates in second half so that each team always shoots in
        the same direction through the match.
        """

        second_half_idx = data.period_id.idxmax()
        columns = [c for c in data.columns if c[-1] in ["x", "y"]]
        if period == 1:
            data.loc[:second_half_idx, columns] *= -1
        else:
            data.loc[second_half_idx:, columns] *= -1

        return data

    def get_frameID_from_timestamp(self, timestamp):
        return self.data.query("timestamp==@timestamp").index[0]

    def get_timestamp(self, mins):
        if ":" in mins:
            seconds = (
                int(mins.split(":")[0]) * 60 + int(mins.split(":")[1]) + 0.04
            )
        else:
            seconds = int(mins) * 60
        return seconds

    def get_frame_data(self, frameID):

        frame_data = self.data.loc[frameID]

        return frame_data

    def get_home_cols(self, frame_data):
        home_cols = []
        for player in self.home_players:
            for col in frame_data.keys():
                if col.startswith(player):
                    home_cols.append(col)
        return home_cols

    def get_away_cols(self, frame_data):
        away_cols = []
        for player in self.away_players:
            for col in frame_data.keys():
                if col.startswith(player):
                    away_cols.append(col)
        return away_cols

    def get_team_pitch_control_traces(self, frame_data, player_num=None):
        pitch_control_dict = generate_pitch_control_for_frame(
            frame_data,
            self.get_home_cols(frame_data),
            self.get_away_cols(frame_data),
        )
        if player_num:
            surface = pitch_control_dict["PPCFa_pax"][str(player_num)]
        else:
            surface = pitch_control_dict["PPCFa"]

        trace = go.Heatmap(
            z=surface,
            x=pitch_control_dict["xgrid"],
            y=pitch_control_dict["ygrid"],
            colorscale="RdBu_r",
            opacity=0.8,
            zsmooth="best",
            zmin=0.0,
            zmax=1.0,
            # showlegend=False,
            colorbar={"len": 0.3, "thickness": 10, "x": 0.9},
            showscale=False,
        )
        # trace = go.Surface(
        # z=surface,
        # colorscale='RdBu_r', opacity=0.8,
        # cmin=0, cmax=1
        # )
        return [trace]

    def position_traces(self, frame_data):
        player_ids = (self.home_players, self.away_players)
        jerseys = (self.home_jerseys, self.away_jerseys)

        position_traces = []
        for i, side in enumerate(["Home", "Away"]):
            players = player_ids[i]
            xlocs = [frame_data[f"{player_id}_x"] for player_id in players]
            ylocs = [frame_data[f"{player_id}_y"] for player_id in players]

            traces = go.Scatter(
                x=xlocs,
                y=ylocs,
                text=jerseys[i],
                **prm.player_marker_args[side],
                name=side,
            )
            position_traces.append(traces)

        return position_traces

    def velocity_traces(self, frame_data):
        player_ids = (self.home_players, self.away_players)
        velocity_quivers = []
        for i, side in enumerate(["Home", "Away"]):
            players = player_ids[i]
            xlocs = [frame_data[f"{player_id}_x"] for player_id in players]
            ylocs = [frame_data[f"{player_id}_y"] for player_id in players]
            xvels = [frame_data[f"{player_id}_vx"] for player_id in players]
            yvels = [frame_data[f"{player_id}_vy"] for player_id in players]

            trace = ff.create_quiver(
                x=xlocs,
                y=ylocs,
                u=xvels,
                v=yvels,
                scale=0.5,
                line_color=prm.player_marker_args[side]["marker_color"],
                name=side + "_vel",
            )
            velocity_quivers.append(trace.data[0])

        return velocity_quivers

    def ball_trace(self, frame_data):
        ball_trace = go.Scatter(
            x=[frame_data["ball_x"]],
            y=[frame_data["ball_y"]],
            marker_size=10,
            marker_opacity=0.8,
            marker_color="white",
            marker_line_width=2,
            marker_line_color="black",
            name="ball",
        )

        return ball_trace

    def get_traces(
        self,
        frameID=None,
        pitch_control=False,
        velocities=True,
        ball=True,
        player_num=None,
    ):
        """Combines various traces for required plot and returns it

        Args:
            velocities (bool, optional): If True, velocity quivers will be added.
            Defaults to True.
            ball (bool, optional): If True, ball trace is added. Defaults to True.
        """
        frame_data = self.get_frame_data(frameID)

        traces = []

        if pitch_control:
            traces.extend(
                self.get_team_pitch_control_traces(
                    frame_data, player_num=player_num
                )
            )

        if velocities:
            traces.extend(self.velocity_traces(frame_data))

        traces.extend(self.position_traces(frame_data))

        if ball:
            traces.append(self.ball_trace(frame_data))

        return traces

    def get_frames(
        self, frame_range, pitch_control=False, velocities=True, ball=True
    ):

        frames = []
        for frameID in tqdm(frame_range):
            data_ = self.get_traces(frameID, pitch_control, velocities, ball)
            name_ = f"f{frameID}"
            frames.append(go.Frame(data=data_, name=name_))

            # frame = {"data": [], "name": str(frameID)}
            # frame["data"].extend(self.get_traces(frameID, pitch_control, velocities, ball))
            # frames.append(frame)

        return frames

    def plot_frame(
        self,
        frameID=None,
        time=None,
        pitch_control=False,
        plot_ball=True,
        show_velocities=False,
        player_num=None,
    ):

        if time:
            seconds = self.get_timestamp(time)
            frameID = self.get_frameID_from_timestamp(seconds)
            if ":" in time:
                time = f"{time.split(':')[0]}' {time.split(':')[1]}\""
            title = f"Time: [{time}'] | FrameID: {frameID}"

        else:
            seconds = self.data.loc[frameID, "timestamp"]
            time = f"{seconds//60:0.0f}'{seconds%60:0.0f}\""
            title = f"Time: [{time}] | FrameID: {frameID}"

        data = self.get_traces(
            frameID=frameID,
            pitch_control=pitch_control,
            velocities=show_velocities,
            ball=plot_ball,
        )
        pitch = Pitch()
        return pitch.plot_freeze_frame(data, title, pitch_control)

    def plot_sequence(
        self,
        f0=None,
        f1=None,
        t0=None,
        t1=None,
        pitch_control=False,
        show_velocities=True,
        player_num=None,
    ):

        if t1:
            t0_ = self.get_timestamp(t0)
            t1_ = self.get_timestamp(t1)

            f0 = self.get_frameID_from_timestamp(t0_)
            f1 = self.get_frameID_from_timestamp(t1_)

            if ":" in t0:
                t0 = f"{t0.split(':')[0]}' {t0.split(':')[1]}\""
            title = f"Time: [{t0}'] | FrameID: {f0} to {f1}"
        else:
            seconds = self.data.loc[f0, "timestamp"]
            t0 = f"{seconds//60:0.0f}'{seconds%60:0.0f}\""
            title = f"Time: [{t0}] | FrameID: {f0} to {f1}"

        frame_range = range(f0, f1)

        data = self.get_traces(
            frameID=f0, pitch_control=pitch_control, velocities=show_velocities
        )
        frames = self.get_frames(
            frame_range, pitch_control=pitch_control, velocities=show_velocities
        )
        pitch = Pitch()
        return pitch.plot_frames_sequence(
            data, frames, frame_range, title, pitch_control
        )


class EventData:
    def __init__(self, events: list):
        self.events = self.add_tags(events)
        for event in self.events:
            tags = event.raw_event["tags"]
            if "SAVED" in tags or "BLOCKED" in tags:
                event.raw_event["marker_color"] = prm.blocked_marker_color
                event.raw_event["marker_line_color"] = prm.marker_border_color
                event.raw_event["marker_line_width"] = prm.marker_border_size

                if "HEAD" in tags:
                    event.raw_event["marker_symbol"] = prm.sym_header
                else:
                    event.raw_event["marker_symbol"] = prm.sym_footer

            elif getattr(event.result, "value", "") == "GOAL":
                event.raw_event["marker_color"] = prm.goal_marker_color
                event.raw_event["marker_line_color"] = prm.marker_border_color
                event.raw_event["marker_line_width"] = prm.marker_border_size

                if "HEAD" in tags:
                    event.raw_event["marker_symbol"] = prm.sym_header
                else:
                    event.raw_event["marker_symbol"] = prm.sym_footer

            else:
                event.raw_event["marker_color"] = "yellow"
                event.raw_event["marker_line_color"] = prm.marker_border_color
                event.raw_event["marker_line_width"] = prm.marker_border_size

                if "HEAD" in tags:
                    event.raw_event["marker_symbol"] = prm.sym_header_off_target
                else:
                    event.raw_event["marker_symbol"] = prm.sym_footer_off_target

        # self.events = events

    def metric_coords(self, event_list):
        for event in event_list:
            # flip sign
            sign = -1 if event.period.id == 1 else 1
            # print(event.raw_event)
            # transform to metric dim (106,68)
            event.raw_event["start"]["X"] = sign * (
                (event.raw_event["start"]["x"] - 0.5) * prm.field_dim[0]
            )
            event.raw_event["start"]["Y"] = sign * (
                -1 * (event.raw_event["start"]["y"] - 0.5) * prm.field_dim[1]
            )
            if event.raw_event["end"]["x"] is not None:
                event.raw_event["end"]["X"] = sign * (
                    (event.raw_event["end"]["x"] - 0.5) * prm.field_dim[0]
                )
                event.raw_event["end"]["Y"] = sign * (
                    -1 * (event.raw_event["end"]["y"] - 0.5) * prm.field_dim[1]
                )
        return event_list

    def add_tags(self, event_list):
        for event in event_list:
            subtypes = event.raw_event.get("subtypes", "")
            tags = []
            if subtypes:
                if isinstance(subtypes, list):
                    tags.extend([x["name"] for x in subtypes])
                else:
                    tags.append(subtypes["name"])
            event.raw_event["tags"] = tags
        return event_list

    def get_shots(self):
        shots = [event for event in self.events if event.event_name == "shot"]
        shots = self.metric_coords(shots)
        return shots

    def get_goals(self):
        goals = [
            event
            for event in self.events
            if getattr(event.result, "value", "") == "GOAL"
        ]
        goals = self.metric_coords(goals)
        return goals

    def get_corners(self):
        corners = []
        for i, event in enumerate(self.events):
            if "CORNER KICK" in event.raw_event.get("tags"):
                corners.append(self.events[i + 1])
        corners = self.metric_coords(corners)
        return corners

    def get_freekicks(self):
        freekicks = []
        for i, event in enumerate(self.events):
            if "FREE KICK" in event.raw_event.get("tags"):
                freekicks.append(self.events[i + 1])
        freekicks = self.metric_coords(freekicks)
        return freekicks

    def get_challenges(self):
        challenges = [
            event for event in self.events if event.event_name == "CHALLENGE"
        ]
        challenges = self.metric_coords(challenges)
        return challenges

    def get_recoveries(self):
        recoveries = [
            event
            for event in self.events
            if event.event_name == "recovery"
            and (
                "INTERCEPTION" in event.raw_event["tags"]
                or "THEFT" in event.raw_event["tags"]
            )
        ]
        recoveries = self.metric_coords(recoveries)
        return recoveries

    def get_turnovers(self):
        turnovers = [
            event
            for event in self.events
            if event.event_name == "pass"
            and (
                "INTERCEPTION" in event.raw_event["tags"]
                or "THEFT" in event.raw_event["tags"]
            )
        ]
        turnovers = self.metric_coords(turnovers)
        return turnovers

    def get_shot_assists(self):
        shot_assists = []  # passes that lead to SHOT/CARRY+SHOT
        for i, event in enumerate(self.events):
            if event.event_name == "shot":
                if self.events[i - 1].event_name == "pass":
                    # passes that led to shots
                    shot_assists.append(self.events[i - 1])
                elif (
                    self.events[i - 1].event_name == "carry"
                    and self.events[i - 2].event_name == "pass"
                ):
                    # passes that led to carry+shot
                    shot_assists.append(self.events[i - 2])

        shot_assists = self.metric_coords(shot_assists)
        return shot_assists

    def get_assists(self):
        assists = []  # passes that lead to GOAL/CARRY+GOAL
        for i, event in enumerate(self.events):
            if getattr(event.result, "value", "") == "GOAL":
                if self.events[i - 1].event_name == "pass":
                    # passes that led to goals
                    assists.append(self.events[i - 1])
                elif (
                    self.events[i - 1].event_name == "carry"
                    and self.events[i - 2].event_name == "pass"
                ):
                    # passes that led to carry+goal
                    assists.append(self.events[i - 2])

        assists = self.metric_coords(assists)
        return assists

    def get_passes(self):
        # only complete passes for now
        passes = [
            event
            for event in self.events
            if event.event_name == "pass" and event.result.value == "COMPLETE"
        ]
        passes = self.metric_coords(passes)
        return passes

    def get_buildup(self, index):
        # PASS/CARRY , ![GENERIC CHALLENGE/RECOVERY]
        buildup = []
        for i, event in enumerate(self.events):
            if event.raw_event["index"] == index:
                team = event.ball_owning_team
                while i > 0:
                    # print (i,self.events[i].raw_event['index'])
                    if self.events[i].result:
                        buildup.append(self.events[i])
                    i -= 1
                    if (
                        self.events[i].ball_owning_team
                        and self.events[i].ball_owning_team != team
                    ):
                        break

        return buildup

    def event_traces(self, row):
        event_traces = []
        x, y, player_nums = [], [], []
        x.extend([row.raw_event["start"]["X"], row.raw_event["end"]["X"]])
        y.extend([row.raw_event["start"]["Y"], row.raw_event["end"]["Y"]])
        if row.event_name == "pass":
            player_nums.extend(
                [row.player.jersey_no, row.receiver_player.jersey_no]
            )
        else:
            player_nums.extend([row.player.jersey_no, None])

        event_traces.append(
            go.Scatter(
                x=x,
                y=y,
                text=player_nums,
                name=row.event_type.name,
                mode="lines+markers+text",
                marker_size=[20, 0],
                # marker_symbol="circle-x",
                marker_color=prm.home_color
                if row.team.ground.name == "HOME"
                else prm.away_color,
                marker_line_color=prm.marker_border_color,
                marker_line_width=[2, 0],
                line_color=prm.home_color
                if row.team.ground.name == "HOME"
                else prm.away_color,
                line_width=1,
                line_dash="dash" if row.event_name == "carry" else None,
                textfont=dict(size=11, color="white"),
                showlegend=False,
            )
        )

        return event_traces

    def get_traces(self, index):
        event_chain = self.get_buildup(index)
        event_chain = self.metric_coords(event_chain)
        traces = []
        for row in event_chain:
            traces.extend(self.event_traces(row))

        return traces

    def title(self, index):
        for row in self.events:
            text = "Event"
            raw = row.raw_event
            if raw["index"] == index:
                time = f"{raw['start']['time']//60:0.0f}'{raw['start']['time']%60:0.0f}\""
                text = f"{raw['type']['name']} > {raw['tags']} > {row.team} | {row.player.name} @ {time}"
                break

        return text

    def plot(self, index=None, type=None, team=None, player=None, trace=False):

        if index:
            pitch = Pitch()
            return pitch.plot_event(
                data=self.get_traces(index), title=self.title(index)
            )

        if type == "shots":
            data = self.get_shots()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[
                            row.raw_event["start"]["X"],
                            row.raw_event["end"]["X"],
                        ],
                        y=[
                            row.raw_event["start"]["Y"],
                            row.raw_event["end"]["Y"],
                        ],
                        text=f"{row.raw_event['tags']}<br>{row.player} ({row.team})",  # [None, None],
                        name=row.result.value,
                        mode="lines+markers" if trace else "markers",
                        marker_size=[15, 0],
                        marker_symbol=row.raw_event["marker_symbol"],
                        marker_color=row.raw_event["marker_color"],
                        marker_line_color=row.raw_event["marker_line_color"],
                        marker_line_width=[
                            row.raw_event["marker_line_width"],
                            0,
                        ],
                        line_color=row.raw_event["marker_line_color"],
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "goals":
            data = self.get_goals()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[
                            row.raw_event["start"]["X"],
                            row.raw_event["end"]["X"],
                        ],
                        y=[
                            row.raw_event["start"]["Y"],
                            row.raw_event["end"]["Y"],
                        ],
                        text=f"{row.result.value}<br>{row.player} ({row.team})",  # [None, None],
                        name=row.result.value,
                        mode="lines+markers" if trace else "markers",
                        marker_size=[15, 0],
                        marker_symbol=row.raw_event["marker_symbol"],
                        marker_color=row.raw_event["marker_color"],
                        marker_line_color=row.raw_event["marker_line_color"],
                        marker_line_width=[
                            row.raw_event["marker_line_width"],
                            0,
                        ],
                        line_color=row.raw_event["marker_line_color"],
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "corners":
            data = self.get_corners()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[
                            row.raw_event["start"]["X"],
                            row.raw_event["end"]["X"],
                        ],
                        y=[
                            row.raw_event["start"]["Y"],
                            row.raw_event["end"]["Y"],
                        ],
                        text=f"{row.result.value}<br>{row.player} ({row.team})",  # [None, None],
                        name=row.result.value,
                        mode="lines+markers" if trace else "markers",
                        marker_size=[0, 10],
                        marker_symbol=prm.sym_corners,
                        marker_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        marker_line_color=prm.marker_border_color,
                        marker_line_width=[0, 2],
                        line_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "freekicks":
            data = self.get_freekicks()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[
                            row.raw_event["start"]["X"],
                            row.raw_event["end"]["X"],
                        ],
                        y=[
                            row.raw_event["start"]["Y"],
                            row.raw_event["end"]["Y"],
                        ],
                        text=f"{row.result.value}<br>{row.player} ({row.team})",  # [None, None],
                        name=row.result.value,
                        mode="lines+markers" if trace else "markers",
                        marker_size=[15, 0],
                        marker_symbol="circle-x",
                        marker_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        marker_line_color=prm.marker_border_color,
                        marker_line_width=[2, 0],
                        line_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "challenges":
            data = self.get_challenges()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[row.raw_event["start"]["X"], None],
                        y=[row.raw_event["start"]["Y"], None],
                        text=f"{row.raw_event['tags']}<br>{row.player} ({row.team})",  # [None, None],
                        name=row.raw_event["tags"][0],
                        mode="markers",
                        marker_size=[18, 0],
                        marker_symbol="hexagon",
                        marker_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        marker_line_color=prm.marker_border_color,
                        marker_line_width=[1, 0],
                        line_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "recoveries":
            data = self.get_recoveries()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[row.raw_event["start"]["X"], None],
                        y=[row.raw_event["start"]["Y"], None],
                        text=f"{row.raw_event['tags']}<br>{row.player} ({row.team})",  # [None, None],
                        name=row.raw_event["tags"][0],
                        mode="markers",
                        marker_size=[18, 0],
                        marker_symbol="hexagon",
                        marker_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        marker_line_color=prm.marker_border_color,
                        marker_line_width=[1, 0],
                        line_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "turnovers":
            data = self.get_turnovers()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[row.raw_event["start"]["X"], None],
                        y=[row.raw_event["start"]["Y"], None],
                        text=f"{row.raw_event['tags']}<br>{row.player} ({row.team})",  # [None, None],
                        name=row.raw_event["tags"][0],
                        mode="markers",
                        marker_size=[18, 0],
                        marker_symbol="hexagon",
                        marker_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        marker_line_color=prm.marker_border_color,
                        marker_line_width=[1, 0],
                        line_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "shot_assists":
            data = self.get_shot_assists()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[
                            row.raw_event["start"]["X"],
                            row.raw_event["end"]["X"],
                        ],
                        y=[
                            row.raw_event["start"]["Y"],
                            row.raw_event["end"]["Y"],
                        ],
                        text=[row.player.jersey_no, None],
                        name=row.result.value,
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[20, 0],
                        marker_symbol="pentagon",
                        marker_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        marker_line_color=prm.marker_border_color,
                        marker_line_width=[2, 0],
                        line_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "assists":
            data = self.get_assists()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[
                            row.raw_event["start"]["X"],
                            row.raw_event["end"]["X"],
                        ],
                        y=[
                            row.raw_event["start"]["Y"],
                            row.raw_event["end"]["Y"],
                        ],
                        text=[row.player.jersey_no, None],
                        name=row.result.value,
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[20, 0],
                        marker_symbol="pentagon",
                        marker_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        marker_line_color=prm.marker_border_color,
                        marker_line_width=[2, 0],
                        line_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "passes":
            data = self.get_passes()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[
                            row.raw_event["start"]["X"],
                            row.raw_event["end"]["X"],
                        ],
                        y=[
                            row.raw_event["start"]["Y"],
                            row.raw_event["end"]["Y"],
                        ],
                        text=[
                            row.player.jersey_no,
                            row.receiver_player.jersey_no,
                        ],
                        name=row.result.value,
                        mode="lines",
                        # marker_size=[0, 0],
                        # marker_symbol=row["marker_symbol"],
                        # marker_color=row["marker_color"],
                        # marker_line_color=row["marker_line_color"],
                        # marker_line_width=[row["marker_line_width"], 0],
                        line_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        line_width=1,
                        # textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "passers":
            data = self.get_passes()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[
                            row.raw_event["start"]["X"],
                            row.raw_event["end"]["X"],
                        ],
                        y=[
                            row.raw_event["start"]["Y"],
                            row.raw_event["end"]["Y"],
                        ],
                        text=[None, None],
                        name=row.result.value,
                        mode="markers+text",
                        marker_size=[10, 0],
                        marker_symbol="diamond",
                        marker_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        marker_line_color=prm.marker_border_color,
                        marker_line_width=[1, 0],
                        # line_color=prm.home_color if row.team.ground.name == "HOME" else prm.away_color,
                        # line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "receivers":
            data = self.get_passes()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[
                            row.raw_event["start"]["X"],
                            row.raw_event["end"]["X"],
                        ],
                        y=[
                            row.raw_event["start"]["Y"],
                            row.raw_event["end"]["Y"],
                        ],
                        text=[None, None],
                        name=row.result.value,
                        mode="markers+text",
                        marker_size=[0, 10],
                        marker_symbol="diamond",
                        marker_color=prm.home_color
                        if row.team.ground.name == "HOME"
                        else prm.away_color,
                        marker_line_color=prm.marker_border_color,
                        marker_line_width=[0, 1],
                        # line_color=prm.home_color if row.team.ground.name == "HOME" else prm.away_color,
                        # line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        pitch = Pitch()
        return pitch.plot_event(
            data=traces, title=type.replace("_", " ").title()
        )
