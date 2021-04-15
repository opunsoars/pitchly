# PITCH VIZ PARAMS
FIELD_WIDTH = 1000
FIELD_HEIGHT = 700
FIELD_DIM = (106.0, 68.0)

FIELD_COLOR = "mediumseagreen"
FIELD_MARKINGS_COLOR = "White"

# FIELD_COLOR = 'White'
# FIELD_MARKINGS_COLOR = 'black'


PLAYERMARKERSIZE = 20
player_marker_args = {
    "Home": dict(
        mode="markers+text",
        marker_size=PLAYERMARKERSIZE,
        marker_line_color="white",
        marker_color="red",
        marker_line_width=2,
        textfont=dict(size=11, color="white"),
    ),
    "Away": dict(
        mode="markers+text",
        marker_size=PLAYERMARKERSIZE,
        marker_line_color="white",
        marker_color="#0570b0",
        marker_line_width=2,
        textfont=dict(size=11, color="white"),
    ),
}

event_player_marker_args = {
    "Home": dict(
        mode="lines+markers+text",
        marker_size=PLAYERMARKERSIZE,
        marker_line_color="white",
        marker_color="red",
        marker_line_width=2,
        line_color="red",
        textfont=dict(size=11, color="white"),
    ),
    "Away": dict(
        mode="lines+markers+text",
        marker_size=PLAYERMARKERSIZE,
        marker_line_color="white",
        marker_color="#0570b0",
        marker_line_width=2,
        line_color="#0570b0",
        textfont=dict(size=11, color="white"),
    ),
}
