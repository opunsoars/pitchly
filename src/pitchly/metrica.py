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

            elif getattr(event.result,'value','')=='GOAL':
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

    def metric_coords(self,event_list):
        for event in event_list:
            # transform to metric dim (106,68)
            event.raw_event["start"]["x"] = (event.raw_event["start"]["x"] - 0.5) * 106.0
            event.raw_event["start"]["y"] = -1 * (event.raw_event["start"]["y"] - 0.5) * 68.0
            event.raw_event["end"]["x"] = (event.raw_event["end"]["x"] - 0.5) * 106.0
            event.raw_event["end"]["y"] = -1 * (event.raw_event["end"]["y"] - 0.5) * 68.0
        return event_list

    def add_tags(self, event_list):
        for event in event_list:
            subtypes = event.raw_event.get('subtypes','')
            tags=[]
            if subtypes:
                if isinstance(subtypes,list):
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
        goals = [event  for event in self.events if getattr(event.result,'value','')=='GOAL']
        goals = self.metric_coords(goals)
        return goals

    def plot(self, index=None, type=None, team=None, player=None, trace=False):
        if type == "shots":
            data = self.get_shots()
            traces = []
            for row in data:
                traces.append(
                    go.Scatter(
                        x=[row.raw_event["start"]["x"], row.raw_event["end"]["x"]],
                        y=[row.raw_event["start"]["y"], row.raw_event["end"]["y"]],
                        text=[None, None],
                        name=row.result.value,
                        mode="lines+markers+text" if trace else "markers+text",
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
                        text=[None, None],
                        name=row.result.value,
                        mode="lines+markers+text" if trace else "markers+text",
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

        pitch = Pitch()
        return pitch.plot_event(data=traces, title=type)