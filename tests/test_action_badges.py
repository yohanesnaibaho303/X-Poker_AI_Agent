from xpoker_agent.vision.actions import parse_action_badge
from xpoker_agent.vision.models import SeatOccupancyObservation


def _occupied() -> SeatOccupancyObservation:
    return SeatOccupancyObservation(
        seat=2,
        status="occupied",
        confidence=0.94,
        dark_panel_fraction=0.4,
        plus_horizontal_pixels=0,
        plus_vertical_pixels=0,
    )


def test_action_badge_accepts_only_exact_supported_labels() -> None:
    assert parse_action_badge(_occupied(), "Fold").action == "fold"
    assert parse_action_badge(_occupied(), "All-in").action == "all_in"
    assert parse_action_badge(_occupied(), "Fo d").action is None


def test_action_badge_never_retains_raw_text() -> None:
    result = parse_action_badge(_occupied(), "Check")
    assert result.ocr_text_sha256 is not None
    assert not hasattr(result, "raw_text")
