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
    cards: list[str]
    hand_class: str | None = None
    big_blind_native: Decimal | None = None
    hero_stack_native: Decimal | None = None
    hero_stack_bb: Decimal | None = None
    pot_native: Decimal | None = None
    pot_bb: Decimal | None = None
    call_amount_native: Decimal | None = None
    call_amount_bb: Decimal | None = None
    effective_stack_bb: Decimal | None = None
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

    big_blind = None
    if status.session_blind_consensus.accepted:
        blind_value = status.session_blind_consensus.value
        if blind_value is not None and "/" in blind_value:
            big_blind = _accepted_decimal(blind_value.split("/", maxsplit=1)[1])
    if big_blind is None or big_blind <= 0:
        big_blind = None
        issues.append("big_blind_not_detected")

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

    hero_stack_bb = hero_stack / big_blind if hero_stack is not None and big_blind else None
    pot_bb = pot / big_blind if pot is not None and big_blind else None
    call_bb = call / big_blind if call is not None and big_blind else None
    opponent_stacks_bb = [
        amount / big_blind
        for opponent, amount in stack_values.items()
        if big_blind is not None
        and amount is not None
        and opponent != seat
        and opponent in status.active_seats
    ]
    effective_bb = (
        effective_stack(hero_stack_bb, *opponent_stacks_bb)
        if hero_stack_bb is not None and opponent_stacks_bb
        else None
    )
    required_equity = (
        pot_odds_required_equity(pot_bb, call_bb)
        if pot_bb is not None and call_bb is not None and call_bb > 0
        else None
    )
    spr = (
        stack_to_pot_ratio(effective_bb, pot_bb)
        if effective_bb is not None and pot_bb is not None and pot_bb > 0
        else None
    )
    return LiveHeroCalculation(
        hero_seat=seat,
        hero_seat_confidence=status.hero_seat_confidence,
        hero_position=status.detected_hero_position,
        cards=cards,
        hand_class=hand_class,
        big_blind_native=big_blind,
        hero_stack_native=hero_stack,
        hero_stack_bb=hero_stack_bb,
        pot_native=pot,
        pot_bb=pot_bb,
        call_amount_native=call,
        call_amount_bb=call_bb,
        effective_stack_bb=effective_bb,
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
