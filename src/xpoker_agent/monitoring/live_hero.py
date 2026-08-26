"""Fail-closed deterministic hero calculations from accepted live observations."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from xpoker_agent.models import Position, StrictModel
from xpoker_agent.poker_math import (
    effective_stack,
    pot_odds_required_equity,
    stack_to_pot_ratio,
)
from xpoker_agent.ranges.cards import canonical_combo, combo_class
from xpoker_agent.vision.models import LiveObservationStatus


class LiveHeroCalculation(StrictModel):
    hero_seat: int | None = None
    hero_seat_confidence: float = 0.0
    hero_position: Position | None = None
    dealt_player_count: int = 0
    range_seat_mismatch: int = 0
    cards: list[str]
    hand_class: str | None = None
    hero_stack_chips: Decimal | None = None
    pot_chips: Decimal | None = None
    call_amount_chips: Decimal | None = None
    effective_stack_chips: Decimal | None = None
    required_equity: Decimal | None = None
    spr: Decimal | None = None
    ready: bool
    issues: list[str]
    assumptions: list[str]


def _accepted_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _call_amount(status: LiveObservationStatus) -> Decimal | None:
    controls = status.hero_control_consensus
    if (
        not controls.accepted
        or controls.value is None
        or not controls.value.startswith("decision:")
    ):
        return None
    token = controls.value.rsplit(":", maxsplit=1)[-1]
    return _accepted_decimal(token) if token else Decimal("0")


def build_live_hero_calculation(status: LiveObservationStatus) -> LiveHeroCalculation:
    issues: list[str] = []
    seat = status.detected_hero_seat
    if seat is None:
        issues.append("hero_seat_not_detected")
    cards = list(status.recognized_hero_cards) if status.hero_cards_accepted else []
    hand_class: str | None = None
    if len(cards) == 2:
        hand_class = combo_class(canonical_combo(cards[0], cards[1]))
    else:
        issues.append("hero_cards_not_detected")
    if status.detected_hero_position is None:
        issues.append("hero_position_not_resolved")

    stack_values = {
        item.seat: _accepted_decimal(item.consensus.value)
        for item in status.seat_stack_consensus
        if item.consensus.accepted
    }
    hero_stack = stack_values.get(seat) if seat is not None else None
    if hero_stack is None:
        issues.append("hero_stack_not_stable")
    pot = (
        _accepted_decimal(status.pot_consensus.value)
        if status.pot_consensus.accepted
        else None
    )
    if pot is None:
        issues.append("pot_not_stable")
    call = _call_amount(status)

    opponent_stacks_chips = [
        amount
        for opponent, amount in stack_values.items()
        if amount is not None
        and opponent != seat
        and opponent in status.active_seats
    ]
    effective_chips = (
        effective_stack(hero_stack, *opponent_stacks_chips)
        if hero_stack is not None and opponent_stacks_chips
        else None
    )
    required_equity = (
        pot_odds_required_equity(pot, call)
        if pot is not None and call is not None and call > 0
        else None
    )
    spr = (
        stack_to_pot_ratio(effective_chips, pot)
        if effective_chips is not None and pot is not None and pot > 0
        else None
    )
    return LiveHeroCalculation(
        hero_seat=seat,
        hero_seat_confidence=status.hero_seat_confidence,
        hero_position=status.detected_hero_position,
        dealt_player_count=len(status.active_seats),
        range_seat_mismatch=max(0, status.table_size - len(status.active_seats)),
        cards=cards,
        hand_class=hand_class,
        hero_stack_chips=hero_stack,
        pot_chips=pot,
        call_amount_chips=call,
        effective_stack_chips=effective_chips,
        required_equity=required_equity,
        spr=spr,
        ready=not issues,
        issues=issues,
        assumptions=[
            "Hero is mapped only from stable local hole-card or action-control evidence.",
            "Effective stack uses the shallowest stable active opponent stack.",
            "Equity and EV remain unavailable until weighted opponent ranges are validated.",
        ],
    )
