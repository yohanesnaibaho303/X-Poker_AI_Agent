"""Privacy-preserving parsing of X-Poker seat-panel OCR."""

from __future__ import annotations

import hashlib
import re

from xpoker_agent.vision.models import SeatOccupancyObservation, SeatPanelObservation
from xpoker_agent.vision.numbers import parse_chip_amount

_AMOUNT_TOKEN = re.compile(r"(?<!\S)(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\S)")


def parse_seat_panel(
    occupancy: SeatOccupancyObservation, ocr_text: str | None
) -> SeatPanelObservation:
    if occupancy.status == "empty":
        return SeatPanelObservation(
            seat=occupancy.seat,
            status="empty",
            confidence=occupancy.confidence,
            reason="empty plus anchor; panel OCR skipped",
        )
    text = (ocr_text or "").strip()
    digest = hashlib.sha256(text.encode()).hexdigest() if text else None
    if "break" in text.casefold():
        return SeatPanelObservation(
            seat=occupancy.seat,
            status="on_break",
            confidence=min(0.8, occupancy.confidence),
            ocr_text_sha256=digest,
            reason="break label observed; OCR remains unbenchmarked",
        )
    tokens = _AMOUNT_TOKEN.findall(text)
    if occupancy.status == "occupied" and tokens:
        token = tokens[-1]
        parsed = parse_chip_amount(token, confidence=min(0.8, occupancy.confidence))
        return SeatPanelObservation(
            seat=occupancy.seat,
            status="seated",
            stack_native=parsed.value,
            stack_token=token,
            confidence=parsed.confidence,
            ocr_text_sha256=digest,
            reason="numeric candidate observed once; temporal acceptance pending",
        )
    return SeatPanelObservation(
        seat=occupancy.seat,
        status="ambiguous",
        confidence=min(0.5, occupancy.confidence),
        ocr_text_sha256=digest,
        reason="occupied panel has no unambiguous stack token",
    )
