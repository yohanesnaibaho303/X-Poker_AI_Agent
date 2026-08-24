"""Fail-closed classification of X-Poker special-rule labels."""

from __future__ import annotations

import re

from xpoker_agent.vision.models import RuleLabelClassification


def classify_rule_label(text: str) -> RuleLabelClassification:
    normalized = " ".join(text.casefold().split())
    signals: list[str] = []
    if "bomb pot" in normalized:
        signals.append("literal_bomb_pot")
    # Windows OCR can lose the small leading word while retaining the distinctive schedule.
    if re.search(r"pot\s*:\s*after\s+\S+\s+hands", normalized):
        signals.append("scheduled_pot_after_hands")
    if signals:
        return RuleLabelClassification(
            supported_standard_nlh=False,
            special_rule="bomb_pot",
            confidence=0.99 if "literal_bomb_pot" in signals else 0.93,
            matched_signals=signals,
            reason="unsupported X-Poker Bomb Pot configuration detected",
        )
    return RuleLabelClassification(
        supported_standard_nlh=False,
        confidence=0.0,
        reason="standard NLH configuration not established by rule-label evidence",
    )
