"""Deterministic X-Poker seat occupancy from versioned layout anchors."""

from __future__ import annotations

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.models import LayoutProfile, NormalizedRect
from xpoker_agent.vision.models import PixelBox, SeatOccupancyObservation
from xpoker_agent.vision.primitives import normalized_box


def _dark_fraction(frame: CapturedFrame, region: NormalizedRect) -> float:
    box = normalized_box(frame, region)
    w = box.right - box.left
    total = w * (box.bottom - box.top)
    frame_width_4 = frame.width * 4
    frame_height = frame.height
    bgra = frame.bgra_bottom_up
    left_4 = box.left * 4
    right_4 = box.right * 4
    dark = 0
    for y in range(box.top, box.bottom):
        source_row = (frame_height - 1 - y) * frame_width_4
        row = bgra[source_row + left_4 : source_row + right_4]
        for i in range(0, len(row), 4):
            if row[i] + row[i + 1] + row[i + 2] < 75:
                dark += 1
    return dark / total


def _plus_strokes(frame: CapturedFrame, box: PixelBox) -> tuple[int, int]:
    radius = max(5, min(12, box.width // 4, box.height // 4))
    width = box.width
    height = box.height
    frame_width_4 = frame.width * 4
    frame_height = frame.height
    bgra = frame.bgra_bottom_up
    left_4 = box.left * 4
    right_4 = box.right * 4

    row_prefix = [0] * (height * (width + 1))
    column_prefix = [0] * (width * (height + 1))

    row_stride = width + 1
    col_stride = height + 1

    for y in range(height):
        source_row = (frame_height - 1 - box.top - y) * frame_width_4
        row = bgra[source_row + left_4 : source_row + right_4]
        row_offset = y * row_stride
        row_total = 0
        for x in range(width):
            idx = x * 4
            b = row[idx]
            g = row[idx + 1]
            r = row[idx + 2]
            neutral = int(
                r >= 90
                and g >= 90
                and b >= 90
                and abs(r - g) <= 45
                and abs(r - b) <= 45
                and abs(g - b) <= 45
            )
            row_total += neutral
            row_prefix[row_offset + x + 1] = row_total
            col_idx = x * col_stride + y
            column_prefix[col_idx + 1] = column_prefix[col_idx] + neutral

    best_h = 0
    best_v = 0
    best_min = 0
    best_sum = 0

    for center_y in range(radius, height - radius):
        row_offset = center_y * row_stride
        h_r_base = row_offset + radius + 1
        h_l_base = row_offset - radius
        for center_x in range(radius, width - radius):
            horizontal = row_prefix[h_r_base + center_x] - row_prefix[h_l_base + center_x]
            col_offset = center_x * col_stride
            vertical = (
                column_prefix[col_offset + center_y + radius + 1]
                - column_prefix[col_offset + center_y - radius]
            )

            cur_min = horizontal if horizontal < vertical else vertical
            cur_sum = horizontal + vertical
            if cur_min > best_min or (cur_min == best_min and cur_sum > best_sum):
                best_h = horizontal
                best_v = vertical
                best_min = cur_min
                best_sum = cur_sum

    return (best_h, best_v)


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
