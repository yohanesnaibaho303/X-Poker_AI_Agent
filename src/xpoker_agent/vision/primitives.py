"""Small dependency-free image primitives over capture-native BGRA frames."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.models import LayoutProfile, NormalizedRect
from xpoker_agent.vision.models import PixelBox


@dataclass(frozen=True)
class BinaryMask:
    width: int
    height: int
    top_down: bytes

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("mask dimensions must be positive")
        if len(self.top_down) != self.width * self.height:
            raise ValueError("mask payload size does not match dimensions")


def validate_frame(frame: CapturedFrame) -> None:
    if frame.width <= 0 or frame.height <= 0:
        raise ValueError("frame dimensions must be positive")
    if len(frame.bgra_bottom_up) != frame.width * frame.height * 4:
        raise ValueError("BGRA payload size does not match frame dimensions")


def normalized_box(frame: CapturedFrame, region: NormalizedRect) -> PixelBox:
    validate_frame(frame)
    left = min(frame.width - 1, round(region.x * frame.width))
    top = min(frame.height - 1, round(region.y * frame.height))
    right = min(frame.width, max(left + 1, round((region.x + region.width) * frame.width)))
    bottom = min(
        frame.height,
        max(top + 1, round((region.y + region.height) * frame.height)),
    )
    return PixelBox(left=left, top=top, right=right, bottom=bottom)


def crop_frame(frame: CapturedFrame, box: PixelBox) -> CapturedFrame:
    """Crop a top-down box while preserving capture-native bottom-up storage."""
    validate_frame(frame)
    if box.right > frame.width or box.bottom > frame.height:
        raise ValueError("crop box extends outside frame")
    rows: list[bytes] = []
    for source_y_bottom_up in range(frame.height - box.bottom, frame.height - box.top):
        start = (source_y_bottom_up * frame.width + box.left) * 4
        rows.append(frame.bgra_bottom_up[start : start + box.width * 4])
    return CapturedFrame(box.width, box.height, b"".join(rows))


def crop_layout_region(
    frame: CapturedFrame, layout: LayoutProfile, region_name: str
) -> CapturedFrame:
    """Extract only a declared layout region, preventing accidental full-frame consumers."""
    try:
        region = layout.regions[region_name]
    except KeyError as error:
        raise ValueError(f"unknown declared layout region: {region_name}") from error
    return crop_frame(frame, normalized_box(frame, region))


def bright_neutral_mask(
    frame: CapturedFrame,
    *,
    minimum_channel: int = 175,
    maximum_channel_spread: int = 65,
) -> BinaryMask:
    """Find light, low-saturation card-like surfaces in top-down order."""
    validate_frame(frame)
    if not 0 <= minimum_channel <= 255 or not 0 <= maximum_channel_spread <= 255:
        raise ValueError("thresholds must be bytes")
    mask = bytearray(frame.width * frame.height)
    for y_top in range(frame.height):
        y_bottom = frame.height - 1 - y_top
        source_row = y_bottom * frame.width * 4
        target_row = y_top * frame.width
        for x in range(frame.width):
            offset = source_row + x * 4
            blue, green, red = frame.bgra_bottom_up[offset : offset + 3]
            bright = min(blue, green, red) >= minimum_channel
            neutral = max(blue, green, red) - min(blue, green, red) <= maximum_channel_spread
            mask[target_row + x] = int(bright and neutral)
    return BinaryMask(frame.width, frame.height, bytes(mask))


def connected_components(mask: BinaryMask, *, minimum_area: int = 1) -> list[PixelBox]:
    """Return four-connected component bounds in deterministic reading order."""
    if minimum_area < 1:
        raise ValueError("minimum area must be positive")
    visited = bytearray(len(mask.top_down))
    components: list[PixelBox] = []
    for seed in range(len(mask.top_down)):
        if not mask.top_down[seed] or visited[seed]:
            continue
        visited[seed] = 1
        queue = deque([seed])
        area = 0
        min_x = mask.width
        max_x = -1
        min_y = mask.height
        max_y = -1
        while queue:
            index = queue.popleft()
            y, x = divmod(index, mask.width)
            area += 1
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
            neighbours = []
            if x:
                neighbours.append(index - 1)
            if x + 1 < mask.width:
                neighbours.append(index + 1)
            if y:
                neighbours.append(index - mask.width)
            if y + 1 < mask.height:
                neighbours.append(index + mask.width)
            for neighbour in neighbours:
                if mask.top_down[neighbour] and not visited[neighbour]:
                    visited[neighbour] = 1
                    queue.append(neighbour)
        if area >= minimum_area:
            components.append(
                PixelBox(left=min_x, top=min_y, right=max_x + 1, bottom=max_y + 1)
            )
    return sorted(components, key=lambda box: (box.top, box.left))

