from decimal import Decimal
from math import isclose
from uuid import UUID

import pytest

from xpoker_agent.models import ComboStrategy, Street, WeightedRange
from xpoker_agent.ranges.cards import (
    DECK,
    all_combos,
    all_hand_classes,
    canonical_combo,
    combo_class,
    expand_hand_class,
    matrix_coordinates,
    split_combo,
)
from xpoker_agent.ranges.engine import (
    action_frequency,
    aggregate_classes,
    apply_blockers,
    bomb_pot_participation_range,
    condition_on_action,
    normalized_combo_probabilities,
    uniform_range,
)
from xpoker_agent.ranges.stack import interpolation_bracket, nearest_stack_bucket

HAND_ID = UUID("30000000-0000-0000-0000-000000000001")


def _range(combos: dict[str, ComboStrategy]) -> WeightedRange:
    return WeightedRange(
        player_ref="villain-1",
        hand_id=HAND_ID,
        street=Street.PREFLOP,
        spot_key="UTG_RFI_100BB_2BB",
        combos=combos,
        source={
            "variant": "NLH",
            "format": "cash",
            "seats": 9,
            "rake": 0,
            "open_size_chips": 2.0,
            "kind": "test_fixture",
        },
        confidence=1.0,
        version="test-v1",
    )


def test_canonical_deck_and_exact_combo_universe() -> None:
    combos = all_combos()

    assert len(DECK) == 52
    assert len(set(DECK)) == 52
    assert len(combos) == 1326
    assert len(set(combos)) == 1326
    assert all(canonical_combo(*split_combo(combo)) == combo for combo in combos)


def test_standard_169_classes_partition_all_exact_combos() -> None:
    classes = all_hand_classes()
    expanded = [combo for hand_class in classes for combo in expand_hand_class(hand_class)]

    assert len(classes) == 169
    assert len(set(classes)) == 169
    assert len(expanded) == 1326
    assert set(expanded) == set(all_combos())
    assert len(expand_hand_class("AA")) == 6
    assert len(expand_hand_class("AKs")) == 4
    assert len(expand_hand_class("AKo")) == 12


def test_matrix_coordinates_follow_pair_suited_offsuit_convention() -> None:
    assert matrix_coordinates("AA") == (0, 0)
    assert matrix_coordinates("AKs") == (0, 1)
    assert matrix_coordinates("AKo") == (1, 0)
    assert combo_class("AsKs") == "AKs"
    assert combo_class("AsKd") == "AKo"


def test_one_blocker_removes_exactly_fifty_one_combos() -> None:
    original = uniform_range(
        player_ref="villain-1",
        hand_id=HAND_ID,
        street=Street.PREFLOP,
        spot_key="unfiltered",
        source={"kind": "uniform_test"},
        version="test-v1",
    )

    blocked = apply_blockers(original, ["As"])

    assert len(original.combos) == 1326
    assert len(blocked.combos) == 1275
    assert blocked.blocked_cards == ["As"]
    assert all("As" not in split_combo(combo) for combo in blocked.combos)


def test_two_blockers_remove_one_hundred_one_combos() -> None:
    original = uniform_range(
        player_ref="villain-1",
        hand_id=HAND_ID,
        street=Street.FLOP,
        spot_key="after_flop_cards",
        source={"kind": "uniform_test"},
        version="test-v1",
    )

    blocked = apply_blockers(original, ["As", "Kd"])

    assert len(blocked.combos) == 1225


def test_bomb_pot_range_starts_from_full_participation_then_applies_blockers() -> None:
    weighted = bomb_pot_participation_range(
        player_ref="villain-1",
        hand_id=HAND_ID,
        street=Street.FLOP,
        visible_cards=["As", "Kd", "Qs", "Jh", "2c"],
        source={"kind": "deterministic_rule_prior"},
        version="bomb-pot-v1",
    )

    assert len(weighted.combos) == 1081
    assert weighted.source["hand_mode"] == "single_board_bomb_pot"
    assert weighted.source["range_role"] == "mandatory_participation_prior"
    assert weighted.blocked_cards == ["2c", "As", "Jh", "Kd", "Qs"]
    assert "no preflop action filter" in weighted.assumptions[0]


def test_bomb_pot_range_cannot_be_created_for_preflop() -> None:
    with pytest.raises(ValueError, match="begin on the flop"):
        bomb_pot_participation_range(
            player_ref="villain-1",
            hand_id=HAND_ID,
            street=Street.PREFLOP,
            visible_cards=[],
            source={"kind": "deterministic_rule_prior"},
            version="bomb-pot-v1",
        )


def test_action_conditioning_uses_bayesian_combo_mass() -> None:
    weighted = _range(
        {
            "AsAh": ComboStrategy(weight=0.5, actions={"raise": 1.0}),
            "KsKh": ComboStrategy(weight=0.5, actions={"call": 0.75, "raise": 0.25}),
        }
    )

    posterior = condition_on_action(weighted, "raise")

    assert isclose(posterior.combos["AsAh"].weight, 0.8)
    assert isclose(posterior.combos["KsKh"].weight, 0.2)
    assert isclose(sum(strategy.weight for strategy in posterior.combos.values()), 1.0)


def test_range_action_frequency_is_weighted_by_combo_probability() -> None:
    weighted = _range(
        {
            "AsAh": ComboStrategy(weight=3.0 / 4.0, actions={"raise": 1.0}),
            "KsKh": ComboStrategy(weight=1.0 / 4.0, actions={"call": 1.0}),
        }
    )

    assert action_frequency(weighted, "raise") == 0.75
    assert action_frequency(weighted, "call") == 0.25


def test_class_aggregation_and_normalization_are_deterministic() -> None:
    weighted = _range(
        {
            "AsAh": ComboStrategy(weight=0.75),
            "AdAc": ComboStrategy(weight=0.25),
            "KsKh": ComboStrategy(weight=1.0),
        }
    )

    assert aggregate_classes(weighted) == {"AA": 1.0, "KK": 1.0}
    assert aggregate_classes(weighted, normalize=True) == {"AA": 0.5, "KK": 0.5}
    assert normalized_combo_probabilities(weighted) == {
        "AdAc": 0.125,
        "AsAh": 0.375,
        "KsKh": 0.5,
    }


def test_weighted_range_rejects_noncanonical_or_blocked_combos() -> None:
    with pytest.raises(ValueError, match="not canonical"):
        _range({"AhAs": ComboStrategy(weight=1.0)})

    with pytest.raises(ValueError, match="conflicts with a blocked card"):
        WeightedRange(
            player_ref="villain-1",
            hand_id=HAND_ID,
            street=Street.PREFLOP,
            spot_key="invalid",
            combos={"AsAh": ComboStrategy(weight=1.0)},
            blocked_cards=["As"],
            source={"kind": "test_fixture"},
            confidence=1.0,
            version="test-v1",
        )


def test_zero_mass_range_cannot_be_normalized_or_conditioned() -> None:
    weighted = _range({"AsAh": ComboStrategy(weight=0.0, actions={"fold": 1.0})})

    with pytest.raises(ValueError, match="zero total weight"):
        normalized_combo_probabilities(weighted)
    with pytest.raises(ValueError, match="zero probability mass"):
        condition_on_action(weighted, "raise")


def test_stack_bucket_exact_nearest_and_tie_policy_are_explicit() -> None:
    exact = nearest_stack_bucket(Decimal("100"))
    nearest = nearest_stack_bucket(Decimal("90"))
    tie = nearest_stack_bucket(Decimal("45"))

    assert exact.status == "exact"
    assert exact.matched_chips == 100
    assert nearest.status == "nearest"
    assert nearest.matched_chips == 80
    assert nearest.absolute_mismatch_chips == 10
    assert tie.matched_chips == 40


def test_stack_interpolation_reports_both_buckets_and_weight() -> None:
    match = interpolation_bracket(Decimal("90"))

    assert match.status == "interpolated"
    assert match.lower_chips == 80
    assert match.upper_chips == 100
    assert match.upper_weight == Decimal("0.5")


def test_stack_interpolation_falls_back_at_unsupported_edges() -> None:
    shallow = interpolation_bracket(Decimal("10"))
    deep = interpolation_bracket(Decimal("250"))

    assert shallow.status == "nearest" and shallow.matched_chips == 40
    assert deep.status == "interpolated"
