from xpoker_agent.vision.models import SeatOccupancyObservation
from xpoker_agent.vision.panels import parse_seat_panel


def _occupancy(status: str = "occupied") -> SeatOccupancyObservation:
    return SeatOccupancyObservation(
        seat=4,
        status=status,
        confidence=0.96,
        dark_panel_fraction=0.4,
        plus_horizontal_pixels=0,
        plus_vertical_pixels=0,
    )


def test_seat_panel_extracts_only_unambiguous_final_stack_token() -> None:
    result = parse_seat_panel(_occupancy(), "kicaubur... 147")

    assert result.status == "seated"
    assert result.stack_native == 147
    assert result.stack_token == "147"
    assert result.accepted is False
    assert result.ocr_text_sha256 is not None


def test_break_panel_has_no_invented_stack() -> None:
    result = parse_seat_panel(_occupancy(), "Break")

    assert result.status == "on_break"
    assert result.stack_native is None
    assert result.accepted is False


def test_occupied_panel_without_numeric_token_is_ambiguous() -> None:
    result = parse_seat_panel(_occupancy(), "wpnyyp...")

    assert result.status == "ambiguous"
    assert result.stack_native is None


def test_compact_stack_token_is_ambiguous_and_never_calculated() -> None:
    result = parse_seat_panel(_occupancy(), "player 115K")

    assert result.status == "ambiguous"
    assert result.stack_native is None


def test_empty_seat_skips_ocr_and_carries_no_private_text_hash() -> None:
    result = parse_seat_panel(_occupancy("empty"), None)

    assert result.status == "empty"
    assert result.ocr_text_sha256 is None
