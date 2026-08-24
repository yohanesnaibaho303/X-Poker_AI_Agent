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
    schedule = re.search(r"pot\s*:\s*after\s+(?P<count>[0-9o]+)\s+hands", normalized)
    if schedule:
        signals.append("scheduled_pot_after_hands")
        hands_until_bomb = int(schedule.group("count").replace("o", "0"))
        if hands_until_bomb > 0:
            return RuleLabelClassification(
                supported_standard_nlh=True,
                special_rule="bomb_pot",
                bomb_pot_state="scheduled",
                hands_until_bomb=hands_until_bomb,
                confidence=0.99 if "literal_bomb_pot" in signals else 0.93,
                matched_signals=signals,
                reason=(
                    f"standard NLH current hand; single-board Bomb Pot scheduled after "
                    f"{hands_until_bomb} hands"
                ),
            )
        return RuleLabelClassification(
            supported_standard_nlh=False,
            supported_single_board_bomb_pot=True,
            special_rule="bomb_pot",
            bomb_pot_state="active",
            hands_until_bomb=0,
            confidence=0.99 if "literal_bomb_pot" in signals else 0.93,
            matched_signals=signals,
            reason="single-board NLH Bomb Pot hand is active",
        )
    if signals:
        return RuleLabelClassification(
            supported_standard_nlh=False,
            special_rule="bomb_pot",
            bomb_pot_state="ambiguous",
            confidence=0.75,
            matched_signals=signals,
            reason="Bomb Pot feature detected but current-hand state is ambiguous",
        )
    return RuleLabelClassification(
        supported_standard_nlh=False,
        confidence=0.0,
        reason="standard NLH configuration not established by rule-label evidence",
    )
