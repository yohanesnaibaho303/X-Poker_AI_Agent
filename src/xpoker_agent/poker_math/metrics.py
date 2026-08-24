"""Exact Decimal poker metrics for chip-EV decisions."""

from __future__ import annotations

from decimal import Decimal


def _nonnegative(name: str, value: Decimal) -> None:
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _probability(name: str, value: Decimal) -> None:
    if value < 0 or value > 1:
        raise ValueError(f"{name} must be within [0, 1]")


def effective_stack(*stacks_bb: Decimal) -> Decimal:
    if not stacks_bb:
        raise ValueError("effective stack requires at least one stack")
    for stack in stacks_bb:
        _nonnegative("stack", stack)
    return min(stacks_bb)


def pot_odds_required_equity(pot_before_call_bb: Decimal, call_bb: Decimal) -> Decimal:
    _nonnegative("pot", pot_before_call_bb)
    _nonnegative("call", call_bb)
    denominator = pot_before_call_bb + call_bb
    if denominator == 0:
        raise ValueError("pot and call cannot both be zero")
    return call_bb / denominator


def call_ev_bb(equity: Decimal, pot_before_call_bb: Decimal, call_bb: Decimal) -> Decimal:
    _probability("equity", equity)
    _nonnegative("pot", pot_before_call_bb)
    _nonnegative("call", call_bb)
    return equity * pot_before_call_bb - (Decimal("1") - equity) * call_bb


def stack_to_pot_ratio(effective_stack_bb: Decimal, pot_bb: Decimal) -> Decimal:
    _nonnegative("effective stack", effective_stack_bb)
    if pot_bb <= 0:
        raise ValueError("pot must be positive")
    return effective_stack_bb / pot_bb


def minimum_defence_frequency(pot_bb: Decimal, bet_bb: Decimal) -> Decimal:
    if pot_bb <= 0:
        raise ValueError("pot must be positive")
    if bet_bb <= 0:
        raise ValueError("bet must be positive")
    return pot_bb / (pot_bb + bet_bb)


def break_even_bluff_fold_frequency(pot_bb: Decimal, bet_bb: Decimal) -> Decimal:
    if pot_bb <= 0:
        raise ValueError("pot must be positive")
    if bet_bb <= 0:
        raise ValueError("bet must be positive")
    return bet_bb / (pot_bb + bet_bb)


def heads_up_bet_ev_bb(
    fold_probability: Decimal,
    called_equity: Decimal,
    pot_before_bet_bb: Decimal,
    bet_bb: Decimal,
) -> Decimal:
    _probability("fold probability", fold_probability)
    _probability("called equity", called_equity)
    _nonnegative("pot", pot_before_bet_bb)
    _nonnegative("bet", bet_bb)
    called_ev = called_equity * (pot_before_bet_bb + bet_bb) - (
        Decimal("1") - called_equity
    ) * bet_bb
    return fold_probability * pot_before_bet_bb + (
        Decimal("1") - fold_probability
    ) * called_ev

