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
from xpoker_agent.vision.live import build_live_capture_diagnostic
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
        ("2.5K", Decimal("2500.0"), "compact"),
        ("1.25", Decimal("1.25"), "decimal"),
        ("199K", Decimal("199000"), "compact"),
    ],
)
def test_chip_amount_parser_accepts_supported_formats(
    text: str, expected: Decimal, format_id: str
) -> None:
    result = parse_chip_amount(text, confidence=0.99)

    assert result.value == expected
    assert result.format_id == format_id


@pytest.mark.parametrize("text", ["-1", "1,00", "1 000", "1.2.3", "", "12BB", "1,5K"])
def test_chip_amount_parser_rejects_ambiguous_or_unsupported_formats(text: str) -> None:
    with pytest.raises(ValueError, match="chip amount"):
        parse_chip_amount(text, confidence=0.5)


@pytest.mark.parametrize(
    "text",
    [
        "Bomb Pot: After 6 hands (1,000-3,000)",
        "aon-,h Pot: After O handsa 1000-3,000)",
    ],
)
def test_bomb_pot_rule_label_fails_closed_despite_minor_ocr_damage(text: str) -> None:
    result = classify_rule_label(text)

    assert result.supported_standard_nlh is False
    assert result.special_rule == "bomb_pot"
    assert result.confidence >= 0.9


def test_unknown_rule_label_never_establishes_supported_nlh() -> None:
    result = classify_rule_label("NLH")

    assert result.supported_standard_nlh is False
    assert result.special_rule is None


def test_live_capture_diagnostic_quarantines_scoped_bomb_pot_evidence() -> None:
    frame = CapturedFrame(10, 20, b"\x00" * 10 * 20 * 4)
    record = CaptureFrameRecord(
        sequence=0,
        captured_at=datetime.now(UTC),
        monotonic_ns=1,
        authorization_profile_id="authorized-test",
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
            text="Bomb Pot: After 2 hands (1,000-3,000) Blinds: 500/1,000",
            lines=["Bomb Pot: After 2 hands", "Blinds: 500/1,000"],
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

    assert diagnostic.standard_nlh_supported is False
    assert diagnostic.special_rule == "bomb_pot"
    assert diagnostic.rule_confidence == 0.99
    assert diagnostic.pot_text == "POT 4,500"
    assert diagnostic.ocr_latency_ms == 5
    assert set(diagnostic.regions) == {"board", "pot", "rule_label", "seat_ring", "actions"}
