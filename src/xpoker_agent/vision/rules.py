"""Fail-closed classification of X-Poker special-rule labels."""

from __future__ import annotations

import re

from xpoker_agent.vision.models import RuleLabelClassification
from xpoker_agent.vision.numbers import parse_chip_amount


def _ocr_count(value: str) -> int:
    compact = re.sub(r"\s+", "", value)
    return int(compact.replace("o", "0").replace("i", "1").replace("l", "1"))


def classify_rule_label(text: str) -> RuleLabelClassification:
    normalized = " ".join(text.casefold().split())
    for unsupported in ("double board", "omaha", "plo", "short deck", "pineapple"):
        if unsupported in normalized:
            return RuleLabelClassification(
                supported_standard_nlh=False,
                supported_single_board_bomb_pot=False,
                confidence=0.99,
                matched_signals=[f"unsupported_variant_{unsupported.replace(' ', '_')}"],
                reason=f"unsupported game variant or overlay: {unsupported}",
            )
    signals: list[str] = []
    blind_values: dict[str, object] = {}
    blind_match = re.search(
        r"(?:blinds?|alinds?)\s*:\s*(?P<small>\d[\d,.]*(?:\.\d+)?)\s*/\s*"
        r"(?P<big>\d[\d,.]*(?:\.\d+)?)",
        normalized,
    )
    if blind_match:
        small = parse_chip_amount(blind_match.group("small"), confidence=0.99).value
        big = parse_chip_amount(blind_match.group("big"), confidence=0.99).value
        if 0 < small < big:
            blind_values = {
                "small_blind_native": small,
                "big_blind_native": big,
                "blind_confidence": 0.99,
            }
            signals.append("native_blinds")
    if "bomb pot" in normalized:
        signals.append("literal_bomb_pot")
    active = re.search(
        r"bomb\s+pot\s*[\(\[]\s*"
        r"(?P<amount>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*[\)\]]",
        normalized,
    )
    if active:
        contribution = parse_chip_amount(active.group("amount"), confidence=0.99)
        return RuleLabelClassification(
            **blind_values,
            supported_standard_nlh=False,
            supported_single_board_bomb_pot=True,
            special_rule="bomb_pot",
            bomb_pot_state="active",
            hands_until_bomb=0,
            bomb_pot_forced_contribution_native=contribution.value,
            confidence=0.99,
            matched_signals=[*signals, "active_parenthesized_contribution"],
            reason=(
                "single-board NLH Bomb Pot label is active with observed forced "
                f"contribution {contribution.value}"
            ),
        )
    # Windows OCR can lose the small leading word while retaining the distinctive schedule.
    schedule = re.search(
        r"pot\s*:\s*after\s+(?P<count>[0-9oil](?:\s*[0-9oil])*)\s+hands",
        normalized,
    )
    if schedule:
        signals.append("scheduled_pot_after_hands")
        hands_until_bomb = _ocr_count(schedule.group("count"))
        if hands_until_bomb > 0:
            return RuleLabelClassification(
                **blind_values,
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
            **blind_values,
            supported_standard_nlh=False,
            supported_single_board_bomb_pot=True,
            special_rule="bomb_pot",
            bomb_pot_state="active",
            hands_until_bomb=0,
            confidence=0.99 if "literal_bomb_pot" in signals else 0.93,
            matched_signals=signals,
            reason="single-board NLH Bomb Pot hand is active",
        )
    recurring = re.search(
        r"pot\s*:\s*every\s+(?P<count>[0-9oil](?:\s*[0-9oil])*)\s+hands",
        normalized,
    )
    if recurring:
        interval = _ocr_count(recurring.group("count"))
        return RuleLabelClassification(
            **blind_values,
            supported_standard_nlh=True,
            special_rule="bomb_pot",
            bomb_pot_state="scheduled",
            bomb_pot_interval_hands=interval,
            confidence=0.99 if "literal_bomb_pot" in signals else 0.93,
            matched_signals=[*signals, "recurring_pot_every_hands"],
            reason=(
                "standard NLH hands between single-board Bomb Pots scheduled every "
                f"{interval} hands"
            ),
        )
    if "literal_bomb_pot" in signals:
        return RuleLabelClassification(
            **blind_values,
            supported_standard_nlh=False,
            special_rule="bomb_pot",
            bomb_pot_state="ambiguous",
            confidence=0.75,
            matched_signals=signals,
            reason="Bomb Pot feature detected but current-hand state is ambiguous",
        )
    return RuleLabelClassification(
        **blind_values,
        supported_standard_nlh=False,
        confidence=0.0,
        reason="standard NLH configuration not established by rule-label evidence",
    )
