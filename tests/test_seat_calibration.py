from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.layout import load_layout_profile
from xpoker_agent.capture.models import NormalizedRect
from xpoker_agent.vision.primitives import normalized_box
from xpoker_agent.vision.seats import classify_seat_occupancy


def _synthetic_nine_max_frame() -> CapturedFrame:
    width, height = 445, 800
    pixels = bytearray(bytes((40, 40, 40, 255)) * width * height)

    def paint(region: NormalizedRect, color: tuple[int, int, int, int]) -> None:
        box = normalized_box(CapturedFrame(width, height, bytes(pixels)), region)
        for y_top in range(box.top, box.bottom):
            y_bottom = height - 1 - y_top
            for x in range(box.left, box.right):
                offset = (y_bottom * width + x) * 4
                pixels[offset : offset + 4] = bytes(color)

    layout = load_layout_profile(table_size=9)
    for seat in (0, 2, 8):
        paint(layout.seat_anchors[seat].player_panel_region, (0, 0, 0, 255))
    for seat in (1, 3, 4, 5, 6):
        box = normalized_box(
            CapturedFrame(width, height, bytes(pixels)),
            layout.seat_anchors[seat].anchor_region,
        )
        center_x = (box.left + box.right) // 2
        center_y = (box.top + box.bottom) // 2
        for offset in range(-8, 9):
            for x, y in ((center_x + offset, center_y), (center_x, center_y + offset)):
                row = height - 1 - y
                pixel = (row * width + x) * 4
                pixels[pixel : pixel + 4] = bytes((120, 120, 120, 255))
    return CapturedFrame(width, height, bytes(pixels))


def test_nine_max_seat_occupancy_is_deterministic_and_fail_closed() -> None:
    observations = classify_seat_occupancy(
        _synthetic_nine_max_frame(), load_layout_profile(table_size=9)
    )
    by_seat = {observation.seat: observation for observation in observations}

    assert [observation.seat for observation in observations] == list(range(9))
    assert {seat for seat, value in by_seat.items() if value.status == "occupied"} == {0, 2, 8}
    assert {seat for seat, value in by_seat.items() if value.status == "empty"} == {
        1,
        3,
        4,
        5,
        6,
    }
    assert by_seat[7].status == "ambiguous"
