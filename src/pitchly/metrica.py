import plotly.figure_factory as ff
import plotly.graph_objects as go
from tqdm.auto import tqdm

from src.pitchly.params import (
    FIELD_COLOR,
    FIELD_DIM,
    FIELD_HEIGHT,
    FIELD_MARKINGS_COLOR,
    FIELD_WIDTH,
    event_player_marker_args,
    player_marker_args,
)
from src.pitchly.pitch import Pitch


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

    def plot(self, index=None, type=None, team=None, player=None, trace=False):
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

        pitch = Pitch()
        return pitch.plot_event(data=traces, title=type)