import re

import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go
from tqdm.auto import tqdm

from .params import prm
from .pitch import Pitch
from .pitch_control_old import generate_pitch_control_for_frame


class TrackingData:
    def __init__(self, tracking_home, tracking_away):
        self.tracking_home = tracking_home
        self.tracking_away = tracking_away

    def get_mins(self, time):
        if ":" not in time:
            return f"{time}:0.04"
        else:
            return f"{time}.04"

    def get_frameID_from_mins(self, mins):
        return self.tracking_home.query("mins==@mins").index[0]

    def get_frame_data(self, frameID):

        hometeam = self.tracking_home.loc[frameID]
        awayteam = self.tracking_away.loc[frameID]
        frame_data = (hometeam, awayteam)

        return frame_data

    def get_team_pitch_control_traces(self, frame_data, player_num=None):
        pitch_control_dict = generate_pitch_control_for_frame(frame_data)
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

        position_traces = []
        for i, side in enumerate(["Home", "Away"]):
            team_data = frame_data[i]
            player_nums = list(
                set(
                    item
                    for subitem in team_data.keys()
                    for item in subitem.split("_")
                    if item.isdigit()
                )
            )
            xlocs = [
                team_data["{}_{}_{}".format(side, num, "X")]
                for num in player_nums
            ]
            ylocs = [
                team_data["{}_{}_{}".format(side, num, "Y")]
                for num in player_nums
            ]
            traces = go.Scatter(
                x=xlocs,
                y=ylocs,
                text=player_nums,
                **prm.player_marker_args[side],
                name=side,
            )
            position_traces.append(traces)

        return position_traces

    def velocity_traces(self, frame_data):

        velocity_quivers = []
        for i, side in enumerate(["Home", "Away"]):
            team_data = frame_data[i]
            player_nums = list(
                set(
                    item
                    for subitem in team_data.keys()
                    for item in subitem.split("_")
                    if item.isdigit()
                )
            )
            xlocs = [
                team_data["{}_{}_{}".format(side, num, "X")]
                for num in player_nums
            ]
            ylocs = [
                team_data["{}_{}_{}".format(side, num, "Y")]
                for num in player_nums
            ]
            xvels = [
                team_data["{}_{}_{}".format(side, num, "vx")]
                for num in player_nums
            ]
            yvels = [
                team_data["{}_{}_{}".format(side, num, "vy")]
                for num in player_nums
            ]
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

        team_data = frame_data[0]
        ball_trace = go.Scatter(
            x=[team_data["ball_X"]],
            y=[team_data["ball_Y"]],
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
            velocities (bool, optional): If True, velocity quivers will be added. Defaults to True.
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

        return frames

    def plot_frame(
        self,
        frameID=None,
        time=None,
        pitch_control=False,
        plot_ball=True,
        show_velocities=False,
    ):

        if time:
            time = self.get_mins(time)
            frameID = self.get_frameID_from_mins(time)
        else:
            time = self.tracking_home.loc[frameID, "mins"]

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
            t0 = self.get_mins(t0)
            t1 = self.get_mins(t1)

            f0 = self.get_frameID_from_mins(t0)
            f1 = self.get_frameID_from_mins(t1)
        else:
            t0 = self.tracking_home.loc[f0, "mins"]

        frame_range = range(f0, f1)

        title = f"Time: [{t0}] | FrameID: {f0} to {f1}"
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
    def __init__(self, events):
        self.events = events
        self.is_shot = self.events.Type == "SHOT"
        self.is_goal = self.events.Subtype.str.endswith("GOAL", na=False)
        self.is_saved = self.events.Subtype.str.endswith("SAVED", na=False)
        self.is_pass = self.events.Type == "PASS"
        self.is_fk = self.events.Subtype == "FREE KICK"
        self.is_corner = self.events.Subtype == "CORNER KICK"
        self.is_balllost = self.events.Type == "BALL LOST"
        self.is_challenge = self.events.Type == "CHALLENGE"

        for i in self.events.index:
            if not isinstance(self.events.loc[i, "Subtype"], str):
                continue
            # if self.events["Type"].iloc[i] == "SHOT":
            if self.events["Subtype"].iloc[i].endswith("SAVED") or self.events[
                "Subtype"
            ].iloc[i].endswith("BLOCKED"):
                self.events.loc[i, "marker_color"] = "white"
                self.events.loc[i, "marker_line_color"] = "white"
                self.events.loc[i, "marker_line_width"] = 2

                if self.events["Subtype"].iloc[i].startswith("HEAD"):
                    self.events.loc[i, "marker_symbol"] = "circle"
                else:
                    self.events.loc[i, "marker_symbol"] = "triangle-up"

            elif self.events.loc[i, "Subtype"].endswith("GOAL"):
                self.events.loc[i, "marker_color"] = "darkgreen"
                self.events.loc[i, "marker_line_color"] = "white"
                self.events.loc[i, "marker_line_width"] = 2

                if self.events["Subtype"].iloc[i].startswith("HEAD"):
                    self.events.loc[i, "marker_symbol"] = "circle"
                else:
                    self.events.loc[i, "marker_symbol"] = "triangle-up"

            else:
                self.events.loc[i, "marker_color"] = "yellow"
                self.events.loc[i, "marker_line_color"] = "white"
                self.events.loc[i, "marker_line_width"] = 2

                if self.events["Subtype"].iloc[i].startswith("HEAD"):
                    self.events.loc[i, "marker_symbol"] = "circle-open"
                else:
                    self.events.loc[i, "marker_symbol"] = "triangle-up-open"

    def get_passes(self):
        return self.events[self.is_pass]

    def get_shots(self):
        return self.events[self.is_shot]

    def get_goals(self):
        return self.events[self.is_goal]

    def get_corners(self):
        corner_index = self.events[self.is_corner].index

        return self.events.iloc[corner_index + 1]

    def get_freekicks(self):
        fk_index = self.events[self.is_fk].index

        return self.events.iloc[fk_index + 1]

    def get_challenges(self):
        return self.events[self.is_challenge]

    def get_turnovers(self):
        return self.events[self.is_balllost]

    def get_shot_assists(self):
        shots = self.get_shots()
        assist_index = [
            i - 1
            for i in shots.index
            if (self.events.Type.iloc[i - 1] == "PASS")
            or (self.events.Subtype.iloc[i - 1] == "CORNER KICK")
            or (self.events.Subtype.iloc[i - 1] == "FREE KICK")
        ]
        return self.events.iloc[assist_index]

    def get_assists(self):
        goals = self.get_goals()
        assist_index = [
            i - 1
            for i in goals.index
            if (self.events.Type.iloc[i - 1] == "PASS")
            or (self.events.Subtype.iloc[i - 1] == "CORNER KICK")
            or (self.events.Subtype.iloc[i - 1] == "FREE KICK")
        ]
        return self.events.iloc[assist_index]

    def title(self, index):
        row = self.events.iloc[index]
        time = f"{row['Start Time [s]']//60:0.0f}'{row['Start Time [s]']%60:0.0f}\""
        text = f"{row['Type']} > {row['Subtype']} > {row['Team']} {row['From']} @ {time}"
        return text

    def get_buildup(self, index):
        for i, row in self.events.iloc[index - 1 :: -1, :2].iterrows():
            if row["Type"] != "PASS":
                break
        buildup = self.events.iloc[i + 1 : index + 1, :]
        buildup["From_num"] = buildup.From.apply(
            lambda x: re.findall("\d+", str(x))
        ).apply(lambda x: x[0] if len(x) > 0 else None)
        buildup["To_num"] = buildup.To.apply(
            lambda x: re.findall(r"\d+", str(x))
        ).apply(lambda x: x[0] if len(x) > 0 else None)
        buildup["To_prev"] = buildup.To_num.shift(1)
        buildup["Start X Carry"] = buildup["End X"]
        buildup["Start Y Carry"] = buildup["End Y"]
        buildup["End X Carry"] = buildup["Start X"].shift(-1)
        buildup["End Y Carry"] = buildup["Start Y"].shift(-1)
        buildup["carry"] = (
            buildup["Start X Carry"] != buildup["End X Carry"]
        ) | (buildup["Start Y Carry"] != buildup["End Y Carry"])
        buildup.loc[buildup["carry"] == False, "Start X Carry"] = np.nan
        buildup.loc[buildup["carry"] == False, "Start Y Carry"] = np.nan
        buildup.loc[buildup["carry"] == False, "End X Carry"] = np.nan
        buildup.loc[buildup["carry"] == False, "End Y Carry"] = np.nan

        buildup["Start Frame Carry"] = buildup["End Frame"]
        buildup["End Frame Carry"] = buildup["Start Frame"].shift(-1)

        return buildup

    def event_traces(self, row):
        event_traces = []
        x, y, player_nums = [], [], []
        x.extend([row["Start X"], row["End X"]])
        y.extend([row["Start Y"], row["End Y"]])
        side = row["Team"]
        player_nums.extend([row["From_num"], row["To_num"]])

        event_traces.append(
            go.Scatter(
                x=x,
                y=y,
                text=player_nums,
                name=row["Type"],
                **prm.event_player_marker_args[side],
            )
        )

        if (row["Type"] == "PASS") & (row["carry"] == True):
            event_traces.append(
                go.Scatter(
                    x=[row["Start X Carry"], row["End X Carry"]],
                    y=[row["Start Y Carry"], row["End Y Carry"]],
                    text=[row["To_num"]],
                    name="DRIBBLE",
                    line_dash="dash",
                    **prm.event_player_marker_args[side],
                )
            )

        return event_traces

    def get_traces(self, index):
        event_chain = self.get_buildup(index)
        traces = []
        for i, row in event_chain.iterrows():
            traces.extend(self.event_traces(row))

        return traces

    def plot(self, index=None, type=None, team=None, player=None, trace=False):

        if index:
            pitch = Pitch()
            return pitch.plot_event(
                data=self.get_traces(index), title=self.title(index)
            )

        if type == "shots":
            data = self.get_shots()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[None, None],
                        name=row["Type"],
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[15, 0],
                        marker_symbol=row["marker_symbol"],
                        marker_color=row["marker_color"],
                        marker_line_color=row["marker_line_color"],
                        marker_line_width=[row["marker_line_width"], 0],
                        line_color=row["marker_line_color"],
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "goals":
            data = self.get_goals()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[None, None],
                        name=row["Type"],
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[15, 0],
                        marker_symbol=row["marker_symbol"],
                        marker_color=row["marker_color"],
                        marker_line_color=row["marker_line_color"],
                        marker_line_width=[row["marker_line_width"], 0],
                        line_color=row["marker_line_color"],
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "freekicks":
            data = self.get_freekicks()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[None, None],
                        name=row["Type"],
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[15, 0],
                        marker_symbol="circle-x",
                        marker_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[2, 0],
                        line_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "assists":
            data = self.get_assists()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[row["From"].split("Player")[1], None],
                        name=row["Type"],
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[18, 0],
                        marker_symbol="pentagon",
                        marker_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[2, 0],
                        line_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "shot_assists":
            data = self.get_shot_assists()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[row["From"].split("Player")[1], None],
                        name=row["Type"],
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[18, 0],
                        marker_symbol="pentagon",
                        marker_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[2, 0],
                        line_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "corners":
            data = self.get_corners()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[None, None],
                        name=row["Type"],
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[0, 10],
                        marker_symbol="square",
                        marker_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[0, 2],
                        line_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "challenges":
            data = self.get_challenges()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[None, None],
                        name=row["Subtype"],
                        mode="markers+text",
                        marker_size=[18, 0],
                        marker_symbol="hexagon",
                        marker_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[1, 0],
                        line_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "turnovers":
            data = self.get_turnovers()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[None, None],
                        name=row["Subtype"],
                        mode="markers+text",
                        marker_size=[18, 0],
                        marker_symbol="hexagon",
                        marker_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[1, 0],
                        line_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "passes":
            data = self.get_passes()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[None, None],
                        name=row["Type"],
                        mode="lines",
                        # marker_size=[0, 0],
                        # marker_symbol=row["marker_symbol"],
                        # marker_color=row["marker_color"],
                        # marker_line_color=row["marker_line_color"],
                        # marker_line_width=[row["marker_line_width"], 0],
                        line_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        line_width=1,
                        # textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "passers":
            data = self.get_passes()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[None, None],
                        name=row["Type"],
                        mode="markers+text",
                        marker_size=[12, 0],
                        marker_symbol="diamond",
                        marker_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[1, 0],
                        # line_color="#AD0B05" if row["Team"] == "Home" else "#0570B0",
                        # line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        elif type == "receivers":
            data = self.get_passes()
            traces = []
            for i, row in data.iterrows():
                traces.append(
                    go.Scatter(
                        x=[row["Start X"], row["End X"]],
                        y=[row["Start Y"], row["End Y"]],
                        text=[None, None],
                        name=row["Type"],
                        mode="markers+text",
                        marker_size=[0, 12],
                        marker_symbol="diamond",
                        marker_color="#AD0B05"
                        if row["Team"] == "Home"
                        else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[0, 1],
                        # line_color="#AD0B05" if row["Team"] == "Home" else "#0570B0",
                        # line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        pitch = Pitch()
        return pitch.plot_event(data=traces, title=type)
