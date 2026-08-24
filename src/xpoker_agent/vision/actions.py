"""Privacy-safe X-Poker action-badge recognition helpers."""

from __future__ import annotations

import hashlib
import re

from xpoker_agent.capture.models import NormalizedRect, SeatAnchorCalibration
from xpoker_agent.vision.models import SeatActionObservation, SeatOccupancyObservation

_ACTION_LABELS = {
    "fold": "fold",
    "check": "check",
    "call": "call",
    "bet": "bet",
    "raise": "raise",
    "allin": "all_in",
}


def action_badge_region(anchor: SeatAnchorCalibration) -> NormalizedRect:
    """Return the calibrated badge crop relative to a portrait seat avatar."""
    x = max(0.0, anchor.anchor_region.x - 0.06)
    y = max(0.0, anchor.anchor_region.y - 0.025)
    return NormalizedRect(
        x=x,
        y=y,
        width=min(0.20, 1.0 - x),
        height=min(0.07, 1.0 - y),
    )


def parse_action_badge(
    occupancy: SeatOccupancyObservation, text: str | None
) -> SeatActionObservation:
    if occupancy.status == "empty":
        return SeatActionObservation(
            seat=occupancy.seat,
            action=None,
            confidence=occupancy.confidence,
            reason="empty seat; action OCR skipped",
        )
    raw = (text or "").strip()
    digest = hashlib.sha256(raw.encode()).hexdigest() if raw else None
    normalized = re.sub(r"[^a-z]", "", raw.casefold())
    action = _ACTION_LABELS.get(normalized)
    if action is None:
        return SeatActionObservation(
            seat=occupancy.seat,
            action=None,
            confidence=0.0,
            ocr_text_sha256=digest,
            reason="no exact supported action badge",
        )
    return SeatActionObservation(
        seat=occupancy.seat,
        action=action,
        confidence=min(0.9, occupancy.confidence),
        ocr_text_sha256=digest,
        reason="action candidate observed once; temporal acceptance pending",
    )
