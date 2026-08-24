"""Deterministic X-Poker dealer-button candidate detection."""

from __future__ import annotations

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.models import LayoutProfile
from xpoker_agent.vision.models import DealerButtonObservation, PixelBox
from xpoker_agent.vision.primitives import normalized_box


def _rgb(frame: CapturedFrame, x: int, y: int) -> tuple[int, int, int]:
    offset = ((frame.height - 1 - y) * frame.width + x) * 4
    blue, green, red, _ = frame.bgra_bottom_up[offset : offset + 4]
    return red, green, blue


def _bright_neutral(frame: CapturedFrame, x: int, y: int) -> bool:
    red, green, blue = _rgb(frame, x, y)
    return min(red, green, blue) >= 175 and max(red, green, blue) - min(red, green, blue) <= 35


def detect_dealer_button(
    frame: CapturedFrame, layout: LayoutProfile
) -> DealerButtonObservation:
    visited: set[tuple[int, int]] = set()
    candidates: list[tuple[PixelBox, int]] = []
    top = round(frame.height * 0.07)
    bottom = round(frame.height * 0.86)
    for y in range(top, bottom):
        for x in range(frame.width):
            if (x, y) in visited or not _bright_neutral(frame, x, y):
                continue
            pending = [(x, y)]
            visited.add((x, y))
            points: list[tuple[int, int]] = []
            while pending:
                current_x, current_y = pending.pop()
                points.append((current_x, current_y))
                for adjacent in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    adjacent_x, adjacent_y = adjacent
                    if (
                        0 <= adjacent_x < frame.width
                        and top <= adjacent_y < bottom
                        and adjacent not in visited
                        and _bright_neutral(frame, adjacent_x, adjacent_y)
                    ):
                        visited.add(adjacent)
                        pending.append(adjacent)
            left = min(point[0] for point in points)
            right = max(point[0] for point in points) + 1
            component_top = min(point[1] for point in points)
            component_bottom = max(point[1] for point in points) + 1
            width = right - left
            height = component_bottom - component_top
            if 16 <= width <= 19 and 14 <= height <= 16 and 120 <= len(points) <= 300:
                candidates.append(
                    (
                        PixelBox(
                            left=left,
                            top=component_top,
                            right=right,
                            bottom=component_bottom,
                        ),
                        len(points),
                    )
                )
    if len(candidates) != 1:
        return DealerButtonObservation(
            seat=None,
            confidence=0.0,
            reason=f"expected one dealer-button component; observed {len(candidates)}",
        )
    box, pixels = candidates[0]
    center_x = (box.left + box.right) / 2
    center_y = (box.top + box.bottom) / 2
    distances = []
    for anchor in layout.seat_anchors:
        anchor_box = normalized_box(frame, anchor.anchor_region)
        anchor_x = (anchor_box.left + anchor_box.right) / 2
        anchor_y = (anchor_box.top + anchor_box.bottom) / 2
        distance = ((center_x - anchor_x) ** 2 + (center_y - anchor_y) ** 2) ** 0.5
        distances.append((distance, anchor.seat))
    distance, seat = min(distances)
    if distance > 80:
        return DealerButtonObservation(
            seat=None,
            confidence=0.0,
            box=box,
            reason="dealer-button component is not near a calibrated seat",
        )
    return DealerButtonObservation(
        seat=seat,
        confidence=min(0.99, 0.9 + (pixels - 120) / 1000 + (80 - distance) / 1000),
        box=box,
        reason="single-frame dealer candidate; temporal acceptance pending",
    )
