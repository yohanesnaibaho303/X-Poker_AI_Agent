from decimal import Decimal

import pytest

from xpoker_agent.poker_math.evaluator import evaluate_best, evaluate_five
from xpoker_agent.poker_math.metrics import (
    break_even_bluff_fold_frequency,
    call_ev_chips,
    effective_stack,
    heads_up_bet_ev_chips,
    minimum_defence_frequency,
    pot_odds_required_equity,
    stack_to_pot_ratio,
)


@pytest.mark.parametrize(
    ("cards", "category", "tiebreak"),
    [
        (["As", "Kd", "9h", "6c", "3d"], "high_card", (14, 13, 9, 6, 3)),
        (["As", "Ad", "9h", "6c", "3d"], "one_pair", (14, 9, 6, 3)),
        (["As", "Ad", "9h", "9c", "3d"], "two_pair", (14, 9, 3)),
        (["As", "Ad", "Ah", "6c", "3d"], "three_of_a_kind", (14, 6, 3)),
        (["9s", "8d", "7h", "6c", "5d"], "straight", (9,)),
        (["As", "Js", "9s", "6s", "3s"], "flush", (14, 11, 9, 6, 3)),
        (["As", "Ad", "Ah", "6c", "6d"], "full_house", (14, 6)),
        (["As", "Ad", "Ah", "Ac", "3d"], "four_of_a_kind", (14, 3)),
        (["9s", "8s", "7s", "6s", "5s"], "straight_flush", (9,)),
    ],
)
def test_five_card_category_vectors(cards, category, tiebreak) -> None:
    result = evaluate_five(cards)

    assert result.name == category
    assert result.tiebreak == tiebreak


def test_wheel_straight_is_five_high() -> None:
    assert evaluate_five(["As", "2d", "3h", "4c", "5s"]).tiebreak == (5,)


def test_seven_card_evaluator_selects_best_five_cards() -> None:
    result = evaluate_best(["As", "Ad", "Ah", "Ks", "Kd", "Kc", "2h"])

    assert result.name == "full_house"
    assert result.tiebreak == (14, 13)


def test_hand_rank_comparison_uses_category_then_kickers() -> None:
    pair_aces = evaluate_five(["As", "Ad", "9h", "6c", "3d"])
    pair_kings = evaluate_five(["Ks", "Kd", "Qh", "Jc", "Td"])
    straight = evaluate_five(["9s", "8d", "7h", "6c", "5d"])

    assert pair_aces > pair_kings
    assert straight > pair_aces


def test_evaluator_rejects_duplicate_or_wrong_card_count() -> None:
    with pytest.raises(ValueError, match="unique"):
        evaluate_five(["As", "As", "3h", "4c", "5s"])
    with pytest.raises(ValueError, match="exactly five"):
        evaluate_five(["As", "Kd"])


def test_exact_chip_ev_metrics() -> None:
    assert effective_stack(Decimal("100"), Decimal("75"), Decimal("200")) == Decimal("75")
    assert pot_odds_required_equity(Decimal("3"), Decimal("1")) == Decimal("0.25")
    assert call_ev_chips(Decimal("0.25"), Decimal("3"), Decimal("1")) == 0
    assert stack_to_pot_ratio(Decimal("90"), Decimal("10")) == 9
    assert minimum_defence_frequency(Decimal("10"), Decimal("5")) == Decimal(2) / Decimal(3)
    assert break_even_bluff_fold_frequency(Decimal("10"), Decimal("5")) == Decimal(1) / Decimal(3)


def test_heads_up_bet_ev_includes_fold_and_called_branches() -> None:
    result = heads_up_bet_ev_chips(
        fold_probability=Decimal("0.5"),
        called_equity=Decimal("0.25"),
        pot_before_bet_chips=Decimal("10"),
        bet_chips=Decimal("5"),
    )

    assert result == Decimal("5")


@pytest.mark.parametrize(
    "function,args",
    [
        (pot_odds_required_equity, (Decimal("0"), Decimal("0"))),
        (stack_to_pot_ratio, (Decimal("10"), Decimal("0"))),
        (minimum_defence_frequency, (Decimal("10"), Decimal("0"))),
        (call_ev_chips, (Decimal("1.1"), Decimal("10"), Decimal("1"))),
    ],
)
def test_metrics_reject_invalid_domains(function, args) -> None:
    with pytest.raises(ValueError):
        function(*args)
