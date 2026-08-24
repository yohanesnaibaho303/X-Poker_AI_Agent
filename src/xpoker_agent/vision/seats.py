"""Deterministic X-Poker seat occupancy from versioned layout anchors."""

from __future__ import annotations

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.models import LayoutProfile, NormalizedRect
from xpoker_agent.vision.models import PixelBox, SeatOccupancyObservation
from xpoker_agent.vision.primitives import normalized_box


def _rgb(frame: CapturedFrame, x: int, y_top_down: int) -> tuple[int, int, int]:
    y_bottom_up = frame.height - 1 - y_top_down
    offset = (y_bottom_up * frame.width + x) * 4
    blue, green, red, _ = frame.bgra_bottom_up[offset : offset + 4]
    return red, green, blue


def _dark_fraction(frame: CapturedFrame, region: NormalizedRect) -> float:
    box = normalized_box(frame, region)
    dark = 0
    total = box.width * box.height
    for y in range(box.top, box.bottom):
        for x in range(box.left, box.right):
            red, green, blue = _rgb(frame, x, y)
            dark += int((red + green + blue) / 3 < 25)
    return dark / total


def _neutral(red: int, green: int, blue: int) -> bool:
    return min(red, green, blue) >= 90 and max(red, green, blue) - min(red, green, blue) <= 45


def _plus_strokes(frame: CapturedFrame, box: PixelBox) -> tuple[int, int]:
    radius = max(5, min(12, box.width // 4, box.height // 4))
    neutral = [
        [_neutral(*_rgb(frame, box.left + x, box.top + y)) for x in range(box.width)]
        for y in range(box.height)
    ]
    row_prefix = [[0] * (box.width + 1) for _ in range(box.height)]
    column_prefix = [[0] * (box.height + 1) for _ in range(box.width)]
    for y in range(box.height):
        for x in range(box.width):
            row_prefix[y][x + 1] = row_prefix[y][x] + int(neutral[y][x])
            column_prefix[x][y + 1] = column_prefix[x][y] + int(neutral[y][x])
    best = (0, 0)
    for center_y in range(radius, box.height - radius):
        for center_x in range(radius, box.width - radius):
            horizontal = (
                row_prefix[center_y][center_x + radius + 1]
                - row_prefix[center_y][center_x - radius]
            )
            vertical = (
                column_prefix[center_x][center_y + radius + 1]
                - column_prefix[center_x][center_y - radius]
            )
            if (min(horizontal, vertical), horizontal + vertical) > (
                min(best),
                sum(best),
            ):
                best = (horizontal, vertical)
    return best


def classify_seat_occupancy(
    frame: CapturedFrame, layout: LayoutProfile
) -> list[SeatOccupancyObservation]:
    observations: list[SeatOccupancyObservation] = []
    for calibration in layout.seat_anchors:
        dark_fraction = _dark_fraction(frame, calibration.player_panel_region)
        horizontal, vertical = _plus_strokes(
            frame, normalized_box(frame, calibration.anchor_region)
        )
        if dark_fraction >= 0.3:
            status = "occupied"
            confidence = min(0.99, 0.8 + (dark_fraction - 0.3))
        # Idle seats use a plus, while in-hand empty seats use X-Poker's circular OPEN
        # control. Both produce the same long neutral horizontal stroke, but the OPEN
        # glyph has a slightly shorter vertical stroke in the calibrated portrait UI.
        elif dark_fraction <= 0.2 and horizontal >= 10 and vertical >= 8:
            status = "empty"
            confidence = min(0.99, 0.8 + min(horizontal, vertical) / 100)
        else:
            status = "ambiguous"
            distance = min(abs(dark_fraction - 0.2), abs(dark_fraction - 0.3))
            confidence = min(0.75, 0.5 + distance)
        observations.append(
            SeatOccupancyObservation(
                seat=calibration.seat,
                status=status,
                confidence=confidence,
                dark_panel_fraction=dark_fraction,
                plus_horizontal_pixels=horizontal,
                plus_vertical_pixels=vertical,
            )
        )
    return observations
