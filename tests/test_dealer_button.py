from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.vision.dealer import detect_dealer_button
from xpoker_agent.vision.primitives import normalized_box


def test_dealer_button_component_maps_to_nearest_nine_max_seat() -> None:
    width, height = 445, 800
    pixels = bytearray(bytes((20, 20, 20, 255)) * width * height)
    layout = load_layout_profile(table_size=9)
    anchor = normalized_box(
        CapturedFrame(width, height, bytes(pixels)), layout.seat_anchors[6].anchor_region
    )
    left = anchor.left - 20
    top = (anchor.top + anchor.bottom) // 2 - 7
    for y in range(top, top + 15):
        for x in range(left, left + 17):
            offset = ((height - 1 - y) * width + x) * 4
            pixels[offset : offset + 4] = bytes((230, 230, 230, 255))

    result = detect_dealer_button(CapturedFrame(width, height, bytes(pixels)), layout)

    assert result.seat == 6
    assert result.confidence >= 0.9


def test_dealer_button_fails_closed_when_absent() -> None:
    frame = CapturedFrame(445, 800, bytes((20, 20, 20, 255)) * 445 * 800)
    assert detect_dealer_button(frame, load_layout_profile(table_size=9)).seat is None
