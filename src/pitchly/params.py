class prm:
    std = dict(
        field_color="mediumseagreen",
        field_markings_color="White",
        title_color="White",
    )
    pc = dict(
        field_color="White",
        field_markings_color="black",
        title_color="black"
    )

    field_width = 1000
    field_height = 700
    field_dim = (106.0, 68.0)

    player_marker_size = 20

    player_marker_args = {
        "Home": dict(
            mode="markers+text",
            marker_size=player_marker_size,
            marker_line_color="white",
            marker_color="red",
            marker_line_width=2,
            textfont=dict(size=11, color="white"),
        ),
        "Away": dict(
            mode="markers+text",
            marker_size=player_marker_size,
            marker_line_color="white",
            marker_color="#0570b0",
            marker_line_width=2,
            textfont=dict(size=11, color="white"),
        ),
    }

    event_player_marker_args = {
        "Home": dict(
            mode="lines+markers+text",
            marker_size=player_marker_size,
            marker_line_color="white",
            marker_color="red",
            marker_line_width=2,
            line_color="red",
            textfont=dict(size=11, color="white"),
        ),
        "Away": dict(
            mode="lines+markers+text",
            marker_size=player_marker_size,
            marker_line_color="white",
            marker_color="#0570b0",
            marker_line_width=2,
            line_color="#0570b0",
            textfont=dict(size=11, color="white"),
        ),
    }

    event_marker_line_color = "white"
    blocked_marker_color = "white"
    goal_marker_color = "darkgreen"
