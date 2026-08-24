from uuid import UUID

import pytest

from xpoker_agent.models import ComboStrategy, Street, WeightedRange
from xpoker_agent.poker_math.equity import exact_equity, monte_carlo_equity

HAND_ID = UUID("30000000-0000-0000-0000-000000000002")


def _range(*combos: str) -> WeightedRange:
    return WeightedRange(
        player_ref="opponent",
        hand_id=HAND_ID,
        street=Street.RIVER,
        spot_key="equity-test",
        combos={combo: ComboStrategy(weight=1.0) for combo in combos},
        source={"kind": "deterministic_test"},
        confidence=1.0,
        version="test-v1",
    )


def test_exact_equity_on_locked_river_win() -> None:
    result = exact_equity(
        "AsAh",
        [_range("KsKh")],
        ["Ac", "Ad", "2c", "3d", "4h"],
    )

    assert result.exact is True
    assert result.trials == 1
    assert result.equity == 1.0
    assert result.win_probability == 1.0


def test_exact_equity_splits_tied_board_between_two_players() -> None:
    result = exact_equity(
        "3d2c",
        [_range("5d4c")],
        ["As", "Ks", "Qs", "Js", "Ts"],
    )

    assert result.equity == 0.5
    assert result.tie_probability == 1.0


def test_exact_multiway_tie_allocates_fractional_share() -> None:
    result = exact_equity(
        "3d2c",
        [_range("5d4c"), _range("7d6c")],
        ["As", "Ks", "Qs", "Js", "Ts"],
    )

    assert result.equity == pytest.approx(1.0 / 3.0)
    assert result.tie_probability == 1.0


def test_seeded_monte_carlo_is_byte_reproducible_and_multiway() -> None:
    opponents = [
        _range("KsKh", "QsQh", "JsJh"),
        _range("KdKc", "QdQc", "JdJc"),
    ]

    first = monte_carlo_equity(
        "AsAh", opponents, ["2c", "7d", "9h"], trials=500, random_seed=20260824
    )
    second = monte_carlo_equity(
        "AsAh", opponents, ["2c", "7d", "9h"], trials=500, random_seed=20260824
    )

    assert first.model_dump_json() == second.model_dump_json()
    assert first.trials == 500
    assert first.random_seed == 20260824


def test_equity_rejects_blocked_or_empty_opponent_ranges() -> None:
    with pytest.raises(ValueError, match="no legal"):
        exact_equity("AsAh", [_range("AsKd")], ["2c", "3d", "4h", "5s", "9c"])
    with pytest.raises(ValueError, match="at least one opponent"):
        monte_carlo_equity("AsAh", [], [], trials=10, random_seed=1)


def test_exact_equity_respects_state_limit() -> None:
    with pytest.raises(ValueError, match="exceeds configured maximum"):
        exact_equity("AsAh", [_range("KsKh")], [], maximum_states=10)
