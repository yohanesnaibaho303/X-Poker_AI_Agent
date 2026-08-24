import struct

import pytest

from xpoker_agent.capture.frames import (
    CapturedFrame,
    classify_xpoker_window,
    normalize_frame,
)


def test_captured_frame_encodes_valid_32_bit_bmp() -> None:
    frame = CapturedFrame(
        width=2,
        height=1,
        bgra_bottom_up=b"\x00\x00\xff\x00\x00\xff\x00\x00",
    )

    encoded = frame.to_bmp()

    assert encoded[:2] == b"BM"
    assert struct.unpack_from("<I", encoded, 2)[0] == len(encoded)
    assert struct.unpack_from("<I", encoded, 10)[0] == 54
    assert struct.unpack_from("<i", encoded, 18)[0] == 2
    assert struct.unpack_from("<i", encoded, 22)[0] == 1
    assert struct.unpack_from("<H", encoded, 28)[0] == 32
    assert encoded[54:] == frame.bgra_bottom_up


def test_captured_frame_rejects_invalid_payload_size() -> None:
    frame = CapturedFrame(width=2, height=2, bgra_bottom_up=b"too short")

    with pytest.raises(ValueError, match="payload size"):
        frame.to_bmp()


def test_classifier_rejects_frames_too_small_for_xpoker_chrome() -> None:
    frame = CapturedFrame(width=2, height=2, bgra_bottom_up=b"\x00" * 16)

    assert classify_xpoker_window(frame) == ("unknown", 0.0)


def test_classifier_detects_table_hamburger_rows() -> None:
    width, height = 445, 800
    pixels = bytearray(width * height * 4)
    for y_top_down in (26, 27, 34, 35, 36, 43):
        y_bottom_up = height - 1 - y_top_down
        for x in range(20, 44):
            offset = (y_bottom_up * width + x) * 4
            pixels[offset : offset + 4] = b"\xff\xff\xff\x00"
    frame = CapturedFrame(width=width, height=height, bgra_bottom_up=bytes(pixels))

    role, confidence = classify_xpoker_window(frame)

    assert role == "table"
    assert confidence >= 0.9


def test_bmp_round_trip_preserves_bgra_pixels() -> None:
    frame = CapturedFrame(width=2, height=1, bgra_bottom_up=b"\x01\x02\x03\x04" * 2)

    decoded = CapturedFrame.from_bmp(frame.to_bmp())

    assert decoded == frame


def test_normalization_is_deterministic_nearest_neighbor() -> None:
    frame = CapturedFrame(
        width=2,
        height=1,
        bgra_bottom_up=b"\x01\x02\x03\x04\x05\x06\x07\x08",
    )

    normalized = normalize_frame(frame, 4, 2)

    expected_row = b"\x01\x02\x03\x04" * 2 + b"\x05\x06\x07\x08" * 2
    assert normalized.bgra_bottom_up == expected_row * 2
