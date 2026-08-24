"""Privacy-scoped parsing of X-Poker hero decision versus pre-action controls."""

from __future__ import annotations

import hashlib
import re

from xpoker_agent.vision.models import HeroActionControlsObservation
from xpoker_agent.vision.numbers import parse_chip_amount


def parse_hero_action_controls(text: str | None) -> HeroActionControlsObservation:
    normalized = " ".join((text or "").casefold().split())
    digest = hashlib.sha256(normalized.encode()).hexdigest() if normalized else None
    if not normalized:
        return HeroActionControlsObservation(
            mode="absent",
            confidence=0.0,
            reason="no hero-control OCR text",
        )
    pre_actions: list[str] = []
    if re.search(r"\bf\s*/\s*c\b", normalized):
        pre_actions.append("fold_or_check")
    if "call any" in normalized:
        pre_actions.append("call_any")
    if pre_actions:
        return HeroActionControlsObservation(
            mode="pre_action",
            pre_action_toggles=pre_actions,
            confidence=0.96,
            ocr_text_sha256=digest,
            reason="X-Poker pre-action toggles are not current legal actions",
        )

    available: list[str] = []
    for token, action in (
        (r"\bfold\b", "fold"),
        (r"\bcheck\b", "check"),
        (r"\bcall\b", "call"),
        (r"\bbet\b", "bet"),
        (r"\braise\b", "raise"),
        (r"\ball[ -]?in\b", "all_in"),
    ):
        if re.search(token, normalized):
            available.append(action)
    if not available:
        return HeroActionControlsObservation(
            mode="ambiguous",
            confidence=0.0,
            ocr_text_sha256=digest,
            reason="control text does not establish pre-action or decision mode",
        )
    call_amount = None
    call_match = re.search(r"\bcall\s+(?P<amount>\d[\d,.]*(?:\.\d+)?[km]?)", normalized)
    if call_match:
        call_amount = parse_chip_amount(call_match.group("amount"), confidence=0.95).value
    return HeroActionControlsObservation(
        mode="decision",
        available_actions=available,
        call_amount_native=call_amount,
        confidence=0.95,
        ocr_text_sha256=digest,
        reason="current X-Poker decision controls parsed; temporal gate pending",
    )
