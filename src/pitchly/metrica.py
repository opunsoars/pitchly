import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go
from scipy import signal
from tqdm.auto import tqdm

# from src.pitchly.params import FIELD_HEIGHT
# from src.pitchly.params import FIELD_MARKINGS_COLOR
# from src.pitchly.params import FIELD_WIDTH
# from src.pitchly.params import event_player_marker_args
# from src.pitchly.params import FIELD_COLOR
from src.pitchly.params import FIELD_DIM
from src.pitchly.params import player_marker_args
from src.pitchly.pitch import Pitch


class TrackingData:
    def __init__(self, data, metadata):
        self.metadata = metadata
        self.home_players = [x.player_id for x in self.metadata.teams[0].players]
        self.away_players = [x.player_id for x in self.metadata.teams[1].players]
        self.home_jerseys = [x.jersey_no for x in self.metadata.teams[0].players]
        self.away_jerseys = [x.jersey_no for x in self.metadata.teams[1].players]

        data = self.metric_coords(data)
        data = self.calc_player_velocities(data, filter_="moving average")
        data = self.flip_second_half_direction(data)
        self.data = data

    def metric_coords(self, data, field_dimen=FIELD_DIM):
        x_columns = [c for c in data.columns if c.endswith("_x")]
        y_columns = [c for c in data.columns if c.endswith("_y")]
        data[x_columns] = (data[x_columns] - 0.5) * field_dimen[0]
        data[y_columns] = -1 * (data[y_columns] - 0.5) * field_dimen[1]

        return data

    def calc_player_velocities(
        self, data, smoothing=True, filter_="moving average", window=7, polyorder=1, maxspeed=12
    ):
        # Get the player ids
        player_ids = self.home_players + self.away_players
        # Calculate the timestep from one frame to the next. Should always be 0.04 within the same half
        dt = data.timestamp.diff()

        # index of first frame in second half
        second_half_idx = data.period_id.idxmax(2)
        # estimate velocities for players in team
        for player in player_ids:  # cycle through players individually
            # difference player positions in timestep dt to get unsmoothed estimate of velicity
            vx = data[player + "_x"].diff() / dt
            vy = data[player + "_y"].diff() / dt

            if maxspeed > 0:
                # remove unsmoothed data points that exceed the maximum speed (these are most likely position errors)
                raw_speed = np.sqrt(vx ** 2 + vy ** 2)
                vx[raw_speed > maxspeed] = np.nan
                vy[raw_speed > maxspeed] = np.nan

            if smoothing:
                if filter_ == "Savitzky-Golay":
                    # calculate first half velocity
                    vx.iloc[:second_half_idx] = signal.savgol_filter(
                        vx.iloc[:second_half_idx], window_length=window, polyorder=polyorder
                    )
                    vy.iloc[:second_half_idx] = signal.savgol_filter(
                        vy.iloc[:second_half_idx], window_length=window, polyorder=polyorder
                    )
                    # calculate second half velocity
                    vx.iloc[second_half_idx:] = signal.savgol_filter(
                        vx.iloc[second_half_idx:], window_length=window, polyorder=polyorder
                    )
                    vy.iloc[second_half_idx:] = signal.savgol_filter(
                        vy.iloc[second_half_idx:], window_length=window, polyorder=polyorder
                    )
                elif filter_ == "moving average":
                    ma_window = np.ones(window) / window
                    # calculate first half velocity
                    vx.iloc[:second_half_idx] = np.convolve(vx.iloc[:second_half_idx], ma_window, mode="same")
                    vy.iloc[:second_half_idx] = np.convolve(vy.iloc[:second_half_idx], ma_window, mode="same")
                    # calculate second half velocity
                    vx.iloc[second_half_idx:] = np.convolve(vx.iloc[second_half_idx:], ma_window, mode="same")
                    vy.iloc[second_half_idx:] = np.convolve(vy.iloc[second_half_idx:], ma_window, mode="same")

            # put player speed in x,y direction, and total speed back in the data frame
            data[player + "_vx"] = vx
            data[player + "_vy"] = vy
            data[player + "_speed"] = np.sqrt(vx ** 2 + vy ** 2)

        return data

    def flip_second_half_direction(self, data):
        """
        Flip coordinates in second half so that each team always shoots in the same direction through the match.
        """
        second_half_idx = data.period_id.idxmax(2)
        columns = [c for c in data.columns if c[-1] in ["x", "y"]]
        data.loc[second_half_idx:, columns] *= -1
        return data

    def get_frameID_from_timestamp(self, timestamp):
        return self.data.query("timestamp==@timestamp").index[0]

    def get_timestamp(self, mins):
        if ":" in mins:
            seconds = int(mins.split(":")[0]) * 60 + int(mins.split(":")[1]) + 0.04
        else:
            seconds = int(mins) * 60
        return seconds

    def get_frame_data(self, frameID):

        frame_data = self.data.loc[frameID]

        return frame_data

    def position_traces(self, frame_data):
        player_ids = (self.home_players, self.away_players)
        jerseys = (self.home_jerseys, self.away_jerseys)

        position_traces = []
        for i, side in enumerate(["Home", "Away"]):
            players = player_ids[i]
            xlocs = [frame_data[f"{player_id}_x"] for player_id in players]
            ylocs = [frame_data[f"{player_id}_y"] for player_id in players]

            traces = go.Scatter(x=xlocs, y=ylocs, text=jerseys[i], **player_marker_args[side], name=side)
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
                line_color=player_marker_args[side]["marker_color"],
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
            marker_color="black",
            marker_line_width=2,
            marker_line_color="green",
            name="ball",
        )

        return ball_trace

    def get_traces(self, frameID=None, velocities=True, ball=True):
        """Combines various traces for required plot and returns it

        Args:
            velocities (bool, optional): If True, velocity quivers will be added. Defaults to True.
            ball (bool, optional): If True, ball trace is added. Defaults to True.
        """
        frame_data = self.get_frame_data(frameID)

        traces = []
        if velocities:
            traces.extend(self.velocity_traces(frame_data))

        traces.extend(self.position_traces(frame_data))

        if ball:
            traces.append(self.ball_trace(frame_data))

        return traces

    def get_frames(self, frame_range, velocities=True, ball=True):

        frames = []
        for frameID in tqdm(frame_range):
            frame = {"data": [], "name": str(frameID)}
            frame["data"].extend(self.get_traces(frameID, velocities, ball))
            frames.append(frame)

        return frames

    def plot_frame(self, frameID=None, time=None, plot_ball=True, show_velocities=False):

        if time:
            seconds = self.get_timestamp(time)
            frameID = self.get_frameID_from_timestamp(seconds)
        else:
            seconds = self.data.loc[frameID, "timestamp"]
            time = f"{seconds//60:0.0f}'{seconds%60:0.0f}\""

        title = f"Time: [{time}] | FrameID: {frameID}"
        data = self.get_traces(frameID=frameID, velocities=show_velocities, ball=plot_ball)
        pitch = Pitch()
        return pitch.plot_freeze_frame(data, title)

    def plot_sequence(self, f0=None, f1=None, t0=None, t1=None, show_velocities=True, player_num=None):

        if t1:
            t0 = self.get_timestamp(t0)
            t1 = self.get_timestamp(t1)

            f0 = self.get_frameID_from_timestamp(t0)
            f1 = self.get_frameID_from_timestamp(t1)
        else:
            seconds = self.data.loc[f0, "timestamp"]
            t0 = f"{seconds//60:0.0f}'{seconds%60:0.0f}\""

        frame_range = range(f0, f1)

        title = f"Time: [{t0}] | FrameID: {f0} to {f1}"
        data = self.get_traces(frameID=f0, velocities=show_velocities)
        frames = self.get_frames(frame_range, velocities=show_velocities)
        pitch = Pitch()
        return pitch.plot_frames_sequence(data, frames, frame_range, title)


class EventData:
    def __init__(self, events: list):
        events = self.add_tags(events)
        for event in events:
            tags = event.raw_event["tags"]
            if "SAVED" in tags or "BLOCKED" in tags:
                event.raw_event["marker_color"] = "white"
                event.raw_event["marker_line_color"] = "white"
                event.raw_event["marker_line_width"] = 2

                if "HEAD" in tags:
                    event.raw_event["marker_symbol"] = "circle"
                else:
                    event.raw_event["marker_symbol"] = "triangle-up"

            elif getattr(event.result, "value", "") == "GOAL":
                event.raw_event["marker_color"] = "darkgreen"
                event.raw_event["marker_line_color"] = "white"
                event.raw_event["marker_line_width"] = 2

                if "HEAD" in tags:
                    event.raw_event["marker_symbol"] = "circle"
                else:
                    event.raw_event["marker_symbol"] = "triangle-up"

            else:
                event.raw_event["marker_color"] = "yellow"
                event.raw_event["marker_line_color"] = "white"
                event.raw_event["marker_line_width"] = 2

                if "HEAD" in tags:
                    event.raw_event["marker_symbol"] = "circle-open"
                else:
                    event.raw_event["marker_symbol"] = "triangle-up-open"

        self.events = events

    def metric_coords(self, event_list):
        for event in event_list:
            # flip sign
            sign = 1 if event.period.id == 1 else -1
            # print(event.raw_event)
            # transform to metric dim (106,68)
            event.raw_event["start"]["x"] = sign * ((event.raw_event["start"]["x"] - 0.5) * 106.0)
            event.raw_event["start"]["y"] = sign * (-1 * (event.raw_event["start"]["y"] - 0.5) * 68.0)
            if event.raw_event["end"]["x"]:
                event.raw_event["end"]["x"] = sign * ((event.raw_event["end"]["x"] - 0.5) * 106.0)
                event.raw_event["end"]["y"] = sign * (-1 * (event.raw_event["end"]["y"] - 0.5) * 68.0)
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
        goals = [event for event in self.events if getattr(event.result, "value", "") == "GOAL"]
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
        challenges = [event for event in self.events if event.event_name == "CHALLENGE"]
        challenges = self.metric_coords(challenges)
        return challenges

    def get_recoveries(self):
        recoveries = [
            event
            for event in self.events
            if event.event_name == "recovery"
            and ("INTERCEPTION" in event.raw_event["tags"] or "THEFT" in event.raw_event["tags"])
        ]
        recoveries = self.metric_coords(recoveries)
        return recoveries

    def get_turnovers(self):
        turnovers = [
            event
            for event in self.events
            if event.event_name == "pass"
            and ("INTERCEPTION" in event.raw_event["tags"] or "THEFT" in event.raw_event["tags"])
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
                elif self.events[i - 1].event_name == "carry" and self.events[i - 2].event_name == "pass":
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
                elif self.events[i - 1].event_name == "carry" and self.events[i - 2].event_name == "pass":
                    # passes that led to carry+goal
                    assists.append(self.events[i - 2])

        assists = self.metric_coords(assists)
        return assists

    def get_passes(self):
        # only complete passes for now
        passes = [event for event in self.events if event.event_name == "pass" and event.result.value == "COMPLETE"]
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
                    if self.events[i].ball_owning_team and self.events[i].ball_owning_team != team:
                        break

        return buildup

    def event_traces(self, row):
        event_traces = []
        x, y, player_nums = [], [], []
        x.extend([row.raw_event["start"]["x"], row.raw_event["end"]["x"]])
        y.extend([row.raw_event["start"]["y"], row.raw_event["end"]["y"]])
        if row.event_name == "pass":
            player_nums.extend([row.player.jersey_no, row.receiver_player.jersey_no])
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
                marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                marker_line_color="white",
                marker_line_width=[2, 0],
                line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
            return pitch.plot_event(data=self.get_traces(index), title=self.title(index))

        if type == "shots":
            data = self.get_shots()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=f"{row.result.value}<br>{row.player}({row.team})",  # [None, None],
                        name=row.result.value,
                        mode="lines+markers" if trace else "markers",
                        marker_size=[15, 0],
                        marker_symbol=row.raw_event["marker_symbol"],
                        marker_color=row.raw_event["marker_color"],
                        marker_line_color=row.raw_event["marker_line_color"],
                        marker_line_width=[row.raw_event["marker_line_width"], 0],
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=f"{row.result.value}<br>{row.player}({row.team})",  # [None, None],
                        name=row.result.value,
                        mode="lines+markers" if trace else "markers",
                        marker_size=[15, 0],
                        marker_symbol=row.raw_event["marker_symbol"],
                        marker_color=row.raw_event["marker_color"],
                        marker_line_color=row.raw_event["marker_line_color"],
                        marker_line_width=[row.raw_event["marker_line_width"], 0],
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=f"{row.result.value}<br>{row.player}({row.team})",  # [None, None],
                        name=row.result.value,
                        mode="lines+markers" if trace else "markers",
                        marker_size=[0, 10],
                        marker_symbol="square",
                        marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[0, 2],
                        line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=f"{row.result.value}<br>{row.player}({row.team})",  # [None, None],
                        name=row.result.value,
                        mode="lines+markers" if trace else "markers",
                        marker_size=[15, 0],
                        marker_symbol="circle-x",
                        marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[2, 0],
                        line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=f"{row.raw_event['tags']}<br>{row.player}({row.team})",  # [None, None],
                        name=row.raw_event["tags"][0],
                        mode="markers",
                        marker_size=[18, 0],
                        marker_symbol="hexagon",
                        marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[1, 0],
                        line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=f"{row.raw_event['tags']}<br>{row.player}({row.team})",  # [None, None],
                        name=row.raw_event["tags"][0],
                        mode="markers",
                        marker_size=[18, 0],
                        marker_symbol="hexagon",
                        marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[1, 0],
                        line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=f"{row.raw_event['tags']}<br>{row.player}({row.team})",  # [None, None],
                        name=row.raw_event["tags"][0],
                        mode="markers",
                        marker_size=[18, 0],
                        marker_symbol="hexagon",
                        marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[1, 0],
                        line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=[row.player.jersey_no, None],
                        name=row.result.value,
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[18, 0],
                        marker_symbol="pentagon",
                        marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[2, 0],
                        line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=[row.player.jersey_no, None],
                        name=row.result.value,
                        mode="lines+markers+text" if trace else "markers+text",
                        marker_size=[18, 0],
                        marker_symbol="pentagon",
                        marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[2, 0],
                        line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=[row.player.jersey_no, row.receiver_player.jersey_no],
                        name=row.result.value,
                        mode="lines",
                        # marker_size=[0, 0],
                        # marker_symbol=row["marker_symbol"],
                        # marker_color=row["marker_color"],
                        # marker_line_color=row["marker_line_color"],
                        # marker_line_width=[row["marker_line_width"], 0],
                        line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=[None, None],
                        name=row.result.value,
                        mode="markers+text",
                        marker_size=[10, 0],
                        marker_symbol="diamond",
                        marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[1, 0],
                        # line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
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
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=[None, None],
                        name=row.result.value,
                        mode="markers+text",
                        marker_size=[0, 10],
                        marker_symbol="diamond",
                        marker_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        marker_line_color="white",
                        marker_line_width=[0, 1],
                        # line_color="#AD0B05" if row.team.ground.name == "HOME" else "#0570B0",
                        # line_width=1,
                        textfont=dict(size=11, color="white"),
                        showlegend=False,
                    )
                )

        pitch = Pitch()
        return pitch.plot_event(data=traces, title=type)
