from datetime import UTC, datetime
from decimal import Decimal

import pytest

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import CaptureFrameRecord, NormalizedRect
from xpoker_agent.vision.cards import (
    classify_board_geometry,
    detect_card_slots,
    validate_unique_cards,
)
from xpoker_agent.vision.live import _scaled_pot_crop, build_live_capture_diagnostic
from xpoker_agent.vision.models import (
    CardRecognition,
    PixelBox,
    TemporalSample,
    WindowsOcrResult,
)
from xpoker_agent.vision.numbers import parse_chip_amount
from xpoker_agent.vision.primitives import (
    BinaryMask,
    connected_components,
    crop_frame,
    normalized_box,
)
from xpoker_agent.vision.rules import classify_rule_label
from xpoker_agent.vision.temporal import consensus
from xpoker_agent.vision.windows_ocr import _top_down_bgra

_HASHES = [f"{index:064x}" for index in range(1, 8)]


def _frame_with_cards(rows: list[tuple[int, int]]) -> CapturedFrame:
    width = height = 200
    pixels = bytearray(width * height * 4)
    for y_top, count in rows:
        for card_index in range(count):
            left = 15 + card_index * 28
            for y in range(y_top, y_top + 30):
                y_bottom = height - 1 - y
                for x in range(left, left + 20):
                    offset = (y_bottom * width + x) * 4
                    pixels[offset : offset + 4] = b"\xff\xff\xff\xff"
    return CapturedFrame(width, height, bytes(pixels))


def test_crop_uses_top_down_coordinates_and_preserves_bottom_up_storage() -> None:
    # Stored rows are bottom blue then top red.
    frame = CapturedFrame(
        width=2,
        height=2,
        bgra_bottom_up=b"\xff\x00\x00\xff" * 2 + b"\x00\x00\xff\xff" * 2,
    )

    cropped = crop_frame(frame, PixelBox(left=0, top=0, right=2, bottom=1))

    assert cropped.width == 2
    assert cropped.height == 1
    assert cropped.bgra_bottom_up == b"\x00\x00\xff\xff" * 2


def test_windows_ocr_adapter_converts_capture_rows_to_top_down() -> None:
    frame = CapturedFrame(
        width=1,
        height=2,
        bgra_bottom_up=b"\xff\x00\x00\xff" + b"\x00\x00\xff\xff",
    )

    assert _top_down_bgra(frame) == b"\x00\x00\xff\xff" + b"\xff\x00\x00\xff"


def test_live_diagnostic_scales_tiny_pot_crop_before_ocr() -> None:
    frame = CapturedFrame(450, 850, b"\x00" * 450 * 850 * 4)
    layout = load_layout_profile()
    assert layout.regions["pot"] == NormalizedRect(
        x=0.40, y=0.33, width=0.20, height=0.08
    )
    pot = crop_frame(frame, normalized_box(frame, layout.regions["pot"]))
    scaled = _scaled_pot_crop(frame, layout)

    assert (scaled.width, scaled.height) == (pot.width * 4, pot.height * 4)


def test_normalized_box_is_half_open_and_inside_frame() -> None:
    frame = CapturedFrame(100, 200, b"\x00" * 100 * 200 * 4)

    box = normalized_box(frame, NormalizedRect(x=0.1, y=0.2, width=0.5, height=0.25))

    assert box == PixelBox(left=10, top=40, right=60, bottom=90)


def test_connected_components_returns_reading_order_bounds() -> None:
    mask = BinaryMask(
        width=5,
        height=3,
        top_down=bytes(
            [
                0,
                1,
                1,
                0,
                0,
                0,
                1,
                0,
                0,
                1,
                0,
                0,
                0,
                0,
                1,
            ]
        ),
    )

    assert connected_components(mask) == [
        PixelBox(left=1, top=0, right=3, bottom=2),
        PixelBox(left=4, top=1, right=5, bottom=3),
    ]


def test_standard_single_board_row_is_supported() -> None:
    slots = detect_card_slots(_frame_with_cards([(80, 5)]))

    result = classify_board_geometry(slots)

    assert len(slots) == 5
    assert result.unsupported is False
    assert result.board_rows == 1


def test_card_slot_detector_drops_nested_bright_components() -> None:
    frame = _frame_with_cards([(80, 4)])
    pixels = bytearray(frame.bgra_bottom_up)

    def paint(left: int, top: int, right: int, bottom: int) -> None:
        for y_top in range(top, bottom):
            y_bottom = frame.height - 1 - y_top
            for x in range(left, right):
                offset = (y_bottom * frame.width + x) * 4
                pixels[offset : offset + 4] = b"\xff\xff\xff\xff"

    # One card-like outline contains a disconnected rank-like inner component.
    paint(127, 80, 147, 83)
    paint(127, 107, 147, 110)
    paint(127, 83, 130, 107)
    paint(144, 83, 147, 107)
    paint(133, 89, 141, 103)

    slots = detect_card_slots(CapturedFrame(frame.width, frame.height, bytes(pixels)))

    assert len(slots) == 5


def test_multiple_board_rows_fail_closed() -> None:
    slots = detect_card_slots(_frame_with_cards([(25, 3), (80, 5), (140, 3)]))

    result = classify_board_geometry(slots)

    assert result.unsupported is True
    assert "multiple_board_rows" in result.reasons
    assert result.board_rows == 3
    assert result.confidence >= 0.9


def test_more_than_five_cards_in_one_row_is_rejected() -> None:
    result = classify_board_geometry(detect_card_slots(_frame_with_cards([(80, 6)])))

    assert result.unsupported is True
    assert "too_many_board_cards" in result.reasons


def test_duplicate_physical_cards_are_rejected() -> None:
    recognitions = [
        CardRecognition(card="As", confidence=0.99),
        CardRecognition(card="As", confidence=0.98, alternatives=["Ah"]),
    ]

    assert validate_unique_cards(recognitions) == ["duplicate_physical_card:As"]


def test_card_recognition_rejects_invalid_codes() -> None:
    with pytest.raises(ValueError, match="rank plus lowercase suit"):
        CardRecognition(card="1x", confidence=0.9)


def test_temporal_consensus_accepts_three_stable_high_confidence_frames() -> None:
    samples = [
        TemporalSample(frame_sequence=1, content_sha256=_HASHES[0], value="As", confidence=0.98),
        TemporalSample(frame_sequence=2, content_sha256=_HASHES[1], value="As", confidence=0.99),
        TemporalSample(frame_sequence=3, content_sha256=_HASHES[2], value="As", confidence=0.97),
    ]

    result = consensus(samples)

    assert result.accepted is True
    assert result.value == "As"
    assert result.stable_frames == 3


def test_temporal_consensus_rejects_recent_disagreement() -> None:
    samples = [
        TemporalSample(frame_sequence=1, content_sha256=_HASHES[0], value="As", confidence=0.99),
        TemporalSample(frame_sequence=2, content_sha256=_HASHES[1], value="As", confidence=0.99),
        TemporalSample(frame_sequence=3, content_sha256=_HASHES[2], value="Ah", confidence=0.99),
    ]

    result = consensus(samples, minimum_confidence=0.6)

    assert result.accepted is False
    assert result.reason == "insufficient_stable_frames"


def test_temporal_consensus_does_not_count_duplicate_frames() -> None:
    samples = [
        TemporalSample(
            frame_sequence=index,
            content_sha256=_HASHES[0],
            value="As",
            confidence=0.99,
        )
        for index in range(1, 4)
    ]

    result = consensus(samples)

    assert result.accepted is False
    assert result.stable_frames == 1


@pytest.mark.parametrize(
    ("text", "expected", "format_id"),
    [
        ("0", Decimal("0"), "integer"),
        ("81,500", Decimal("81500"), "grouped"),
        ("1.25", Decimal("1.25"), "decimal"),
    ],
)
def test_chip_amount_parser_accepts_supported_formats(
    text: str, expected: Decimal, format_id: str
) -> None:
    result = parse_chip_amount(text, confidence=0.99)

    assert result.value == expected
    assert result.format_id == format_id


@pytest.mark.parametrize("text", ["-1", "1,00", "1 000", "1.2.3", "", "12BB", "1,5K", "2.5K", "1M"])
def test_chip_amount_parser_rejects_ambiguous_or_unsupported_formats(text: str) -> None:
    with pytest.raises(ValueError, match="chip amount"):
        parse_chip_amount(text, confidence=0.5)


def test_scheduled_bomb_pot_does_not_quarantine_current_standard_hand() -> None:
    result = classify_rule_label("Bomb Pot: After 6 hands (1,000-3,000)")

    assert result.supported_standard_nlh is True
    assert result.supported_single_board_bomb_pot is False
    assert result.special_rule == "bomb_pot"
    assert result.bomb_pot_state == "scheduled"
    assert result.hands_until_bomb == 6
    assert result.confidence >= 0.9


def test_scheduled_bomb_pot_normalizes_ocr_letter_i_as_countdown_one() -> None:
    result = classify_rule_label("24 aug Bomb Pot: After I hands (2-4) Blinds: 1/2")

    assert result.supported_standard_nlh is True
    assert result.bomb_pot_state == "scheduled"
    assert result.hands_until_bomb == 1
    assert result.small_blind_native == 1
    assert result.big_blind_native == 2
    assert result.blind_confidence == 0.99
    assert "native_blinds" in result.matched_signals


def test_scheduled_bomb_pot_normalizes_spaced_ocr_digits() -> None:
    result = classify_rule_label("Somb Pot: After I I hands (2-4) Blinds: 1/2")

    assert result.supported_standard_nlh is True
    assert result.hands_until_bomb == 11


def test_active_bomb_pot_is_classified_despite_minor_ocr_damage() -> None:
    result = classify_rule_label("aon-,h Pot: After O handsa 1000-3,000)")

    assert result.supported_standard_nlh is False
    assert result.supported_single_board_bomb_pot is True
    assert result.special_rule == "bomb_pot"
    assert result.bomb_pot_state == "active"


def test_active_bomb_pot_parenthesized_contribution_is_structured() -> None:
    result = classify_rule_label("24 aug Bomb Pot(4) Blinds: 1/2")

    assert result.supported_single_board_bomb_pot is True
    assert result.bomb_pot_state == "active"
    assert result.bomb_pot_forced_contribution_native == 4
    assert "active_parenthesized_contribution" in result.matched_signals
    assert result.hands_until_bomb == 0
    assert result.confidence >= 0.9


def test_recurring_bomb_pot_label_is_scheduled_not_active() -> None:
    result = classify_rule_label("24 aug Bomb Pot: Every 12 hands (2-4) Blinds: 1/2")

    assert result.supported_standard_nlh is True
    assert result.supported_single_board_bomb_pot is False
    assert result.bomb_pot_state == "scheduled"
    assert result.hands_until_bomb is None
    assert result.bomb_pot_interval_hands == 12
    assert "recurring_pot_every_hands" in result.matched_signals


def test_unknown_rule_label_never_establishes_supported_nlh() -> None:
    result = classify_rule_label("NLH")

    assert result.supported_standard_nlh is False
    assert result.special_rule is None


def test_compact_rule_amounts_are_never_calculated() -> None:
    result = classify_rule_label("Bomb Pot(4K) Blinds: 1K/2K")

    assert result.bomb_pot_forced_contribution_native is None
    assert result.small_blind_native is None
    assert result.big_blind_native is None


def test_live_capture_diagnostic_supports_countdown_hand_and_exposes_schedule() -> None:
    frame = CapturedFrame(10, 20, b"\x00" * 10 * 20 * 4)
    record = CaptureFrameRecord(
        sequence=0,
        captured_at=datetime.now(UTC),
        monotonic_ns=1,
        authorization_profile_id="authorized-test",
        target_hwnd=123,
        target_process_id=456,
        target_fingerprint="a" * 64,
        layout_id="xpoker-windows-10-portrait-v1",
        source_width=10,
        source_height=20,
        source_dpi=96,
        width=10,
        height=20,
        dpi=96,
        content_sha256="b" * 64,
        capture_latency_ms=4.5,
        visual_role_confidence=0.95,
    )
    diagnostic = build_live_capture_diagnostic(
        frame=frame,
        record=record,
        layout=load_layout_profile(),
        rule_ocr=WindowsOcrResult(
            text="Bomb Pot: After 2 hands (1,000-3,000) Blinds: 1/2",
            lines=["Bomb Pot: After 2 hands", "Blinds: 1/2"],
            processing_latency_ms=3,
            language_tag="en-US",
        ),
        pot_ocr=WindowsOcrResult(
            text="POT 4,500",
            lines=["POT 4,500"],
            processing_latency_ms=2,
            language_tag="en-US",
        ),
    )

    assert diagnostic.current_hand_supported is True
    assert diagnostic.table_size == 9
    assert diagnostic.current_hand_mode == "standard_nlh"
    assert diagnostic.standard_nlh_supported is True
    assert diagnostic.single_board_bomb_pot_supported is False
    assert diagnostic.bomb_pot_state == "scheduled"
    assert diagnostic.hands_until_bomb == 2
    assert diagnostic.special_rule == "bomb_pot"
    assert diagnostic.rule_confidence == 0.99
    assert diagnostic.pot_text == "POT 4,500"
    assert diagnostic.board_rows == 0
    assert diagnostic.board_card_slots == 0
    assert diagnostic.board_geometry_supported is True
    assert diagnostic.ocr_latency_ms == 5
    assert {
        "board",
        "hero_cards",
        "pot",
        "rule_label",
        "seat_ring",
        "actions",
    }.issubset(diagnostic.regions)
    assert all(f"seat_{seat}_anchor" in diagnostic.regions for seat in range(9))
