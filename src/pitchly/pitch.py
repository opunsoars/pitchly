from collections import namedtuple

import plotly.graph_objects as go

from src.pitchly.params import FIELD_COLOR  # event_player_marker_args,; player_marker_args,
from src.pitchly.params import FIELD_DIM
from src.pitchly.params import FIELD_HEIGHT
from src.pitchly.params import FIELD_MARKINGS_COLOR
from src.pitchly.params import FIELD_WIDTH


class Pitch:
    def __init__(self):
        # ALL DIMENSIONS IN m
        self.border_dimen = (3, 3)  # include a border arround of the field of width 3m
        self.meters_per_yard = 0.9144  # unit conversion from yards to meters
        self.half_pitch_length = FIELD_DIM[0] / 2.0  # length of half pitch
        self.half_pitch_width = FIELD_DIM[1] / 2.0  # width of half pitch
        self.signs = [-1, 1]
        # Soccer field dimensions typically defined in yards, so we need to convert to meters
        self.goal_line_width = 8 * self.meters_per_yard
        self.box_width = 20 * self.meters_per_yard
        self.box_length = 6 * self.meters_per_yard
        self.area_width = 44 * self.meters_per_yard
        self.area_length = 18 * self.meters_per_yard
        self.penalty_spot = 12 * self.meters_per_yard
        self.corner_radius = 1 * self.meters_per_yard
        self.D_length = 8 * self.meters_per_yard
        self.D_radius = 10 * self.meters_per_yard
        self.D_pos = 12 * self.meters_per_yard
        self.centre_circle_radius = 10 * self.meters_per_yard

        self.point = namedtuple("point", ["x", "y"])
        self.centre = self.point(0.0, 0.0)

    def get_layout(self, time=None, frameID=None, frame_range=None, title=None):
        shapes = []

        mid_circle = dict(
            type="circle",
            x0=self.centre.x - self.centre_circle_radius,
            y0=self.centre.y - self.centre_circle_radius,
            x1=self.centre.x + self.centre_circle_radius,
            y1=self.centre.y + self.centre_circle_radius,
            line_color=FIELD_MARKINGS_COLOR,
            layer="below",
        )
        mid_line = dict(
            type="line",
            x0=self.centre.x,
            y0=self.centre.y - self.half_pitch_width,
            x1=self.centre.x,
            y1=self.centre.y + self.half_pitch_width,
            line_color=FIELD_MARKINGS_COLOR,
            layer="below",
        )
        mid_point = dict(
            type="circle",
            x0=self.centre.x - 0.4,
            y0=self.centre.y - 0.4,
            x1=self.centre.x + 0.4,
            y1=self.centre.y + 0.4,
            line_color=FIELD_MARKINGS_COLOR,
            fillcolor=FIELD_MARKINGS_COLOR,
            layer="below",
        )
        shapes.extend([mid_circle, mid_line, mid_point])

        for s in self.signs:

            # plot pitch boundary
            boundary1 = dict(
                type="line",
                x0=-self.half_pitch_length,
                y0=s * self.half_pitch_width,
                x1=self.half_pitch_length,
                y1=s * self.half_pitch_width,
                line_color=FIELD_MARKINGS_COLOR,
                layer="below",
            )

            boundary2 = dict(
                type="line",
                x0=s * self.half_pitch_length,
                y0=-self.half_pitch_width,
                x1=s * self.half_pitch_length,
                y1=self.half_pitch_width,
                line_color=FIELD_MARKINGS_COLOR,
                layer="below",
            )

            circle = dict(
                type="circle",
                x0=s * (self.centre.x + self.half_pitch_length - self.penalty_spot) - self.centre_circle_radius,
                y0=self.centre.y - self.centre_circle_radius,
                x1=s * (self.centre.x + self.half_pitch_length - self.penalty_spot) + self.centre_circle_radius,
                y1=self.centre.y + self.centre_circle_radius,
                line_color=FIELD_MARKINGS_COLOR,
                layer="below",
            )

            patch = dict(
                type="rect",
                x0=s * self.half_pitch_length,
                y0=-self.area_width / 2.0 - 1,
                x1=s * (self.half_pitch_length - self.area_length),
                y1=self.area_width / 2.0 + 1,
                line=dict(color=FIELD_COLOR, width=0),
                fillcolor=FIELD_COLOR,
                layer="below",
            )

            box = dict(
                type="rect",
                x0=s * self.half_pitch_length,
                y0=-self.area_width / 2.0,
                x1=s * (self.half_pitch_length - self.area_length),
                y1=self.area_width / 2.0,
                line=dict(color=FIELD_MARKINGS_COLOR, width=2),
                layer="below",
            )
            D = dict(
                type="rect",
                x0=s * self.half_pitch_length,
                y0=-self.box_width / 2.0,
                x1=s * (self.half_pitch_length - self.box_length),
                y1=self.box_width / 2.0,
                line=dict(color=FIELD_MARKINGS_COLOR, width=2),
                layer="below",
            )
            pen = dict(
                type="circle",
                x0=s * (self.half_pitch_length - self.penalty_spot) - 0.4,
                y0=-0.4,
                x1=s * (self.half_pitch_length - self.penalty_spot) + 0.4,
                y1=0.4,
                line_color=FIELD_MARKINGS_COLOR,
                fillcolor=FIELD_MARKINGS_COLOR,
                layer="below",
            )

            top_post = dict(
                type="rect",
                x0=s * self.half_pitch_length,
                y0=self.goal_line_width / 2.0 - 0.5,
                x1=s * (self.half_pitch_length - 0.5),
                y1=self.goal_line_width / 2.0 + 0.5,
                line=dict(color=FIELD_MARKINGS_COLOR, width=0),
                fillcolor=FIELD_MARKINGS_COLOR,
                layer="below",
            )

            bottom_post = dict(
                type="rect",
                x0=s * self.half_pitch_length,
                y0=-self.goal_line_width / 2.0 - 0.5,
                x1=s * (self.half_pitch_length - 0.5),
                y1=-self.goal_line_width / 2.0 + 0.5,
                line=dict(color=FIELD_MARKINGS_COLOR, width=0),
                fillcolor=FIELD_MARKINGS_COLOR,
                layer="below",
            )

            shapes.extend([boundary1, boundary2, circle, patch, box, D, pen, top_post, bottom_post])

            # set axis limits
        xmax = FIELD_DIM[0] / 2.0 + self.border_dimen[0]
        ymax = FIELD_DIM[1] / 2.0 + self.border_dimen[1]

        layout = go.Layout(
            title={
                "text": f"Time: [{time}] | FrameID: {frameID}",
                "y": 0.99,
                "x": 0.5,
                "xanchor": "center",
                "yanchor": "top",
                "font_color": "white",
                "font_size": 20,
            },
            hovermode="closest",
            autosize=True,
            width=FIELD_WIDTH,
            height=FIELD_HEIGHT,
            plot_bgcolor=FIELD_COLOR,
            xaxis=go.layout.XAxis(
                range=[-xmax, xmax], showgrid=False, zeroline=False, showticklabels=False, visible=False
            ),
            yaxis=go.layout.YAxis(
                range=[-ymax, ymax],
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                visible=False,
                scaleanchor="x",
                scaleratio=1,
            ),
            margin=go.layout.Margin(l=0, r=0, b=0, t=0, pad=0),
            legend=dict(x=0.1, y=-0.01, orientation="h"),
        )

        layout["shapes"] = shapes

        if frame_range:
            layout["sliders"], layout["updatemenus"] = self.add_controls(frame_range)
            layout["title"] = None
            layout["margin"]["b"] = 100

        if title:
            layout["title_text"] = title

        return layout

    def plot_freeze_frame(self, data, title):
        fig_dict = {"data": [], "layout": {}, "frames": []}

        fig_dict["layout"] = self.get_layout(title=title)
        fig_dict["data"] = data

        fig = go.Figure(fig_dict)
        fig.show()

    def plot_frames_sequence(self, data, frames, frame_range, title):
        fig_dict = {"data": [], "layout": {}, "frames": []}

        fig_dict["layout"] = self.get_layout(frame_range=frame_range, title=title)
        fig_dict["data"] = data
        fig_dict["frames"] = frames

        fig = go.Figure(fig_dict)
        fig.show()

    def add_controls(self, frames_to_track):
        sliders_dict = {
            "active": 0,
            #     "yanchor": "top",
            #     "xanchor": "left",
            "currentvalue": {"font": {"size": 20}, "prefix": "Frame:", "visible": True, "xanchor": "right"},
            "transition": {"duration": 300, "easing": "cubic-in-out"},
            "pad": {"b": 0, "t": 0},
            #     "len": 0.9,
            #     "x": 0.1,
            #     "y": 0,
            "steps": [],
        }

        for frameID in frames_to_track:
            slider_step = {
                "args": [
                    [frameID],
                    {
                        "frame": {"duration": 300, "redraw": False},
                        "mode": "immediate",
                        "transition": {"duration": 0, "easing": "linear"},
                    },
                ],
                "label": frameID,
                "method": "animate",
            }
            sliders_dict["steps"].append(slider_step)

        updatemenus = {
            "buttons": [
                {
                    "args": [
                        None,
                        {
                            "frame": {"duration": 0, "redraw": False},
                            "fromcurrent": True,
                            "mode": "immediate",
                            "transition": {"duration": 0, "easing": "linear"},
                        },
                    ],
                    "label": ">",
                    "method": "animate",
                },
                {
                    "args": [
                        [None],
                        {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}},
                    ],
                    "label": "||",
                    "method": "animate",
                },
            ],
            "direction": "left",
            # "font":{"size":10},
            # "pad": {"r": 40, "t": 50},
            "showactive": False,
            "type": "buttons",
            "xanchor": "right",
            "yanchor": "top",
            "x": 0.1,
            "y": 0,
        }

        return [sliders_dict], [updatemenus]

    def plot_event(self, data, title):
        fig_dict = {"data": [], "layout": {}, "frames": []}

        fig_dict["layout"] = self.get_layout(title=title)
        fig_dict["data"] = data

        fig = go.Figure(fig_dict)
        fig.show()
