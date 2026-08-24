"""Fail-closed parsing for the X-Poker pot label."""

from __future__ import annotations

import re

from xpoker_agent.vision.models import PotObservation
from xpoker_agent.vision.numbers import parse_chip_amount

_POT_LABEL = re.compile(
    r"^\s*(?P<label>P[O0A][TR7])\s*:?\s*"
    r"(?P<amount>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?[KkMm]?)\s*$",
    re.IGNORECASE,
)


def parse_pot_label(text: str) -> PotObservation:
    match = _POT_LABEL.fullmatch(text)
    if match is None:
        return PotObservation(
            confidence=0.0,
            reason="pot label does not contain exactly one unambiguous amount",
        )
    token = match.group("amount")
    label = match.group("label").casefold()
    confidence = 0.95 if label == "pot" else 0.8
    amount = parse_chip_amount(token, confidence=confidence)
    return PotObservation(
        value_native=amount.value,
        token=token,
        confidence=amount.confidence,
        reason=(
            "numeric pot candidate observed once; temporal acceptance pending"
            if label == "pot"
            else "known stylized-label OCR alias; temporal acceptance pending"
        ),
    )
