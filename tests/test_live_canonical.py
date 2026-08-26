from decimal import Decimal

import pytest

from xpoker_agent.vision.canonical import build_standard_live_hand_prefix
from xpoker_agent.vision.models import BlindPostReconciliation


def _blind_posts() -> list[BlindPostReconciliation]:
    return [
        BlindPostReconciliation(
            hand_epoch=1,
            seat=1,
            blind_kind="small_blind",
            amount_native=Decimal("1"),
            stack_delta_event_id="a" * 64,
            status="matched",
            reason="test evidence",
        ),
        BlindPostReconciliation(
            hand_epoch=1,
            seat=2,
            blind_kind="big_blind",
            amount_native=Decimal("2"),
            stack_delta_event_id="b" * 64,
            status="matched",
            reason="test evidence",
        ),
    ]


def _build(**overrides: object):
    values = {
        "target_fingerprint": "authorized-xpoker-test-table",
        "hand_epoch": 1,
        "table_size": 9,
        "hero_seat": 0,
        "dealer_seat": 0,
        "starting_stacks_native": {
            0: Decimal("100"),
            1: Decimal("100"),
            2: Decimal("100"),
        },
        "current_stacks_native": {
            0: Decimal("100"),
            1: Decimal("99"),
            2: Decimal("98"),
        },
        "current_pot_native": Decimal("3"),
        "big_blind_native": Decimal("2"),
        "blind_posts": _blind_posts(),
        "hero_cards": ["As", "Kd"],
        "board_cards": [],
        "actions": [],
        "amount_reconciliations": [],
    }
    values.update(overrides)
    return build_standard_live_hand_prefix(**values)


def test_builds_a_deterministic_reducer_validated_live_prefix() -> None:
    first = _build()
    second = _build()

    assert first == second
    assert [event.type for event in first.events] == [
        "hand_started",
        "dealer_assigned",
        "blind_posted",
        "blind_posted",
        "hole_cards_observed",
    ]
    assert first.state.next_to_act_seat == 0
    assert first.state.pot_main_chips == Decimal("3")
    assert first.state.hero_cards == ["As", "Kd"]
    assert not first.complete


def test_rejects_board_when_preflop_action_evidence_is_incomplete() -> None:
    with pytest.raises(ValueError, match="betting round closes"):
        _build(board_cards=["2c", "7d", "Jh"])


def test_rejects_live_stack_that_disagrees_with_reducer() -> None:
    with pytest.raises(ValueError, match="seat 0"):
        _build(
            current_stacks_native={
                0: Decimal("98"),
                1: Decimal("99"),
                2: Decimal("98"),
            }
        )
