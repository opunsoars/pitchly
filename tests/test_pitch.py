from pitchly.pitch import Pitch


def test_pitch_returns_figure():
    figure = Pitch().plot_pitch(show=False)
    assert figure is not None


def test_pitch_plot_event_returns_figure():
    figure = Pitch().plot_event(data=None, title=None, show=False)
    assert figure is not None


def test_pitch_plot_frames_sequence_returns_figure():
    figure = Pitch().plot_frames_sequence(
        data=None,
        frames=None,
        frame_range=range(0, 0),
        pitch_control=False,
        title=None,
        show=False
    )
    assert figure is not None


def test_pitch_plot_freeze_frame_returns_figure():
    figure = Pitch().plot_freeze_frame(
        data=None,
        title=None,
        pitch_control=False,
        show=False
    )
    assert figure is not None
