"""X-Poker card-surface geometry and unsupported-board rejection."""

from __future__ import annotations

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.vision.models import (
    CardRecognition,
    CardSlotCandidate,
    UnsupportedVisualState,
)
from xpoker_agent.vision.primitives import bright_neutral_mask, connected_components


def detect_card_slots(frame: CapturedFrame) -> list[CardSlotCandidate]:
    """Detect rectangular light card surfaces; rank/suit classification is a later stage."""
    minimum_width = max(5, round(frame.width * 0.035))
    maximum_width = max(minimum_width, round(frame.width * 0.25))
    minimum_height = max(8, round(frame.height * 0.045))
    maximum_height = max(minimum_height, round(frame.height * 0.42))
    minimum_area = max(20, minimum_width * minimum_height // 3)
    boxes = connected_components(bright_neutral_mask(frame), minimum_area=minimum_area)
    candidates: list[CardSlotCandidate] = []
    for box in boxes:
        aspect = box.width / box.height
        if not (
            minimum_width <= box.width <= maximum_width
            and minimum_height <= box.height <= maximum_height
            and 0.38 <= aspect <= 0.92
        ):
            continue
        aspect_score = max(0.0, 1.0 - abs(aspect - 0.67) / 0.35)
        candidates.append(CardSlotCandidate(box=box, confidence=0.7 + 0.25 * aspect_score))
    outermost = [
        candidate
        for candidate in candidates
        if not any(
            other.box.left <= candidate.box.left
            and other.box.top <= candidate.box.top
            and other.box.right >= candidate.box.right
            and other.box.bottom >= candidate.box.bottom
            and other.box.width * other.box.height
            >= candidate.box.width * candidate.box.height * 2
            for other in candidates
            if other is not candidate
        )
    ]
    return assign_card_rows(outermost)


def assign_card_rows(candidates: list[CardSlotCandidate]) -> list[CardSlotCandidate]:
    if not candidates:
        return []
    ordered = sorted(
        candidates,
        key=lambda item: ((item.box.top + item.box.bottom) / 2, item.box.left),
    )
    median_height = sorted(item.box.height for item in ordered)[len(ordered) // 2]
    tolerance = max(3.0, median_height * 0.45)
    row_centres: list[float] = []
    assigned: list[CardSlotCandidate] = []
    for candidate in ordered:
        centre = (candidate.box.top + candidate.box.bottom) / 2
        row = next(
            (
                index
                for index, row_centre in enumerate(row_centres)
                if abs(centre - row_centre) <= tolerance
            ),
            None,
        )
        if row is None:
            row = len(row_centres)
            row_centres.append(centre)
        assigned.append(candidate.model_copy(update={"row_index": row}))
    return sorted(assigned, key=lambda item: (item.row_index, item.box.left))


def classify_board_geometry(candidates: list[CardSlotCandidate]) -> UnsupportedVisualState:
    row_counts: dict[int, int] = {}
    for candidate in candidates:
        row_counts[candidate.row_index] = row_counts.get(candidate.row_index, 0) + 1
    credible_rows = [count for count in row_counts.values() if count >= 2]
    reasons: list[str] = []
    if len(credible_rows) > 1:
        reasons.append("multiple_board_rows")
    if any(count > 5 for count in row_counts.values()):
        reasons.append("too_many_board_cards")
    if candidates and not credible_rows:
        reasons.append("ambiguous_board_geometry")
    confidence = 0.0
    if reasons:
        confidence = min(0.99, 0.75 + 0.06 * len(candidates) + 0.08 * len(reasons))
    return UnsupportedVisualState(
        unsupported=bool(reasons),
        reasons=reasons,
        confidence=confidence,
        board_rows=len(credible_rows),
        card_slots=len(candidates),
    )


def validate_unique_cards(recognitions: list[CardRecognition]) -> list[str]:
    """Reject physically impossible duplicate cards before state reconstruction."""
    cards = [recognition.card for recognition in recognitions]
    duplicates = sorted({card for card in cards if cards.count(card) > 1})
    return [f"duplicate_physical_card:{card}" for card in duplicates]
