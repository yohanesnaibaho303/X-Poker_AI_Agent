"""Deterministic X-Poker dealer-button candidate detection."""

from __future__ import annotations

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.models import LayoutProfile
from xpoker_agent.vision.models import DealerButtonObservation, PixelBox
from xpoker_agent.vision.primitives import (
    bright_neutral_mask,
    connected_components,
    crop_frame,
    normalized_box,
)


def detect_dealer_button(
    frame: CapturedFrame, layout: LayoutProfile
) -> DealerButtonObservation:
    candidates: list[tuple[PixelBox, int]] = []
    top = round(frame.height * 0.07)
    bottom = round(frame.height * 0.86)
    crop = crop_frame(frame, PixelBox(left=0, top=top, right=frame.width, bottom=bottom))
    mask = bright_neutral_mask(crop, minimum_channel=175, maximum_channel_spread=35)
    for component in connected_components(mask, minimum_area=120):
        pixels = sum(
            sum(
                mask.top_down[
                    y * mask.width + component.left : y * mask.width + component.right
                ]
            )
            for y in range(component.top, component.bottom)
        )
        if 16 <= component.width <= 19 and 14 <= component.height <= 16 and pixels <= 300:
            candidates.append(
                (
                    PixelBox(
                        left=component.left,
                        top=component.top + top,
                        right=component.right,
                        bottom=component.bottom + top,
                    ),
                    pixels,
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
