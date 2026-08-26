"""Exact Decimal poker metrics for chip-EV decisions."""

from __future__ import annotations

from decimal import Decimal


def _nonnegative(name: str, value: Decimal) -> None:
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _probability(name: str, value: Decimal) -> None:
    if value < 0 or value > 1:
        raise ValueError(f"{name} must be within [0, 1]")


def effective_stack(*stacks_chips: Decimal) -> Decimal:
    if not stacks_chips:
        raise ValueError("effective stack requires at least one stack")
    for stack in stacks_chips:
        _nonnegative("stack", stack)
    return min(stacks_chips)


def pot_odds_required_equity(pot_before_call_chips: Decimal, call_chips: Decimal) -> Decimal:
    _nonnegative("pot", pot_before_call_chips)
    _nonnegative("call", call_chips)
    denominator = pot_before_call_chips + call_chips
    if denominator == 0:
        raise ValueError("pot and call cannot both be zero")
    return call_chips / denominator


def call_ev_chips(equity: Decimal, pot_before_call_chips: Decimal, call_chips: Decimal) -> Decimal:
    _probability("equity", equity)
    _nonnegative("pot", pot_before_call_chips)
    _nonnegative("call", call_chips)
    return equity * pot_before_call_chips - (Decimal("1") - equity) * call_chips


def stack_to_pot_ratio(effective_stack_chips: Decimal, pot_chips: Decimal) -> Decimal:
    _nonnegative("effective stack", effective_stack_chips)
    if pot_chips <= 0:
        raise ValueError("pot must be positive")
    return effective_stack_chips / pot_chips


def minimum_defence_frequency(pot_chips: Decimal, bet_chips: Decimal) -> Decimal:
    if pot_chips <= 0:
        raise ValueError("pot must be positive")
    if bet_chips <= 0:
        raise ValueError("bet must be positive")
    return pot_chips / (pot_chips + bet_chips)


def break_even_bluff_fold_frequency(pot_chips: Decimal, bet_chips: Decimal) -> Decimal:
    if pot_chips <= 0:
        raise ValueError("pot must be positive")
    if bet_chips <= 0:
        raise ValueError("bet must be positive")
    return bet_chips / (pot_chips + bet_chips)


def heads_up_bet_ev_chips(
    fold_probability: Decimal,
    called_equity: Decimal,
    pot_before_bet_chips: Decimal,
    bet_chips: Decimal,
) -> Decimal:
    _probability("fold probability", fold_probability)
    _probability("called equity", called_equity)
    _nonnegative("pot", pot_before_bet_chips)
    _nonnegative("bet", bet_chips)
    called_ev = (
        called_equity * (pot_before_bet_chips + bet_chips)
        - (Decimal("1") - called_equity) * bet_chips
    )
    return fold_probability * pot_before_bet_chips + (Decimal("1") - fold_probability) * called_ev
