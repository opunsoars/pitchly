class prm:
    std = dict(
        field_color="mediumseagreen",
        field_markings_color="White",
        title_color="White",
    )
    pc = dict(
        field_color="White", field_markings_color="black", title_color="black"
    )

    field_width = 1000
    field_height = 700
    field_dim = (106.0, 68.0)

    marker_border_color = "white"
    marker_border_size = 2

    blocked_marker_color = "white"
    goal_marker_color = "#EE3124"

    home_color = "#AD0B05"
    away_color = "#0570B0"
    player_marker_size = 20

    # symbols
    sym_header = "circle"
    sym_header_off_target = "circle-open"
    sym_footer = "triangle-up"
    sym_footer_off_target = "triangle-up-open"
    sym_corners = "square"

    # sizes -> corners [10] fks [15] chlnge/recov/turnov [18] rest [20]

    player_marker_args = {
        "Home": dict(
            mode="markers+text",
            marker_size=player_marker_size,
            marker_line_color=marker_border_color,
            marker_color=home_color,
            marker_line_width=marker_border_size,
            textfont=dict(size=11, color="white"),
        ),
        "Away": dict(
            mode="markers+text",
            marker_size=player_marker_size,
            marker_line_color=marker_border_color,
            marker_color=away_color,
            marker_line_width=marker_border_size,
            textfont=dict(size=11, color="white"),
        ),
    }

    event_player_marker_args = {
        "Home": dict(
            mode="lines+markers+text",
            marker_size=player_marker_size,
            marker_line_color=marker_border_color,
            marker_color=home_color,
            marker_line_width=marker_border_size,
            line_color=home_color,
            textfont=dict(size=11, color="white"),
        ),
        "Away": dict(
            mode="lines+markers+text",
            marker_size=player_marker_size,
            marker_line_color=marker_border_color,
            marker_color=away_color,
            marker_line_width=marker_border_size,
            line_color=away_color,
            textfont=dict(size=11, color="white"),
        ),
    }
