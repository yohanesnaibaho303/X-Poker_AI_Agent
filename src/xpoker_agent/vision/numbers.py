"""Strict parsing boundary for X-Poker chip amounts after OCR."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from xpoker_agent.vision.models import NumericRecognition

_AMOUNT_PATTERN = re.compile(
    r"^(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"(?P<suffix>[KkMm])?$"
)


def parse_chip_amount(raw_text: str, *, confidence: float) -> NumericRecognition:
    """Parse only unambiguous X-Poker numeric formats; malformed OCR fails closed."""
    text = raw_text.strip()
    if not text or any(character.isspace() for character in text):
        raise ValueError("chip amount contains empty or embedded whitespace")
    match = _AMOUNT_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"unsupported or ambiguous chip amount format: {raw_text!r}")
    number_text = match.group("number")
    suffix = match.group("suffix")
    try:
        value = Decimal(number_text.replace(",", ""))
    except InvalidOperation as error:
        raise ValueError(f"invalid chip amount: {raw_text!r}") from error
    if suffix:
        value *= Decimal("1000") if suffix.casefold() == "k" else Decimal("1000000")
        format_id = "compact"
    elif "," in number_text:
        format_id = "grouped"
    elif "." in number_text:
        format_id = "decimal"
    else:
        format_id = "integer"
    return NumericRecognition(
        raw_text=raw_text,
        value=value,
        confidence=confidence,
        format_id=format_id,
    )
