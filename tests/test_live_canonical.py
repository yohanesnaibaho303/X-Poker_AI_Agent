from decimal import Decimal

import pytest

from xpoker_agent.models import Position
from xpoker_agent.vision.canonical import (
    build_standard_live_hand_prefix,
    complete_single_winner_live_hand,
)
from xpoker_agent.vision.live_observation import LiveObservationService
from xpoker_agent.vision.models import (
    ActionAmountReconciliation,
    BlindPostReconciliation,
    DerivedActionCandidate,
    LiveHandBoundaryValidation,
    StackIncreaseCandidate,
)


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


def _closed_prefix():
    actions = [
        DerivedActionCandidate(
            event_id=event_id * 64,
            hand_epoch=1,
            frame_sequence=sequence,
            seat=seat,
            street="preflop",
            action="fold",
            confidence=0.95,
        )
        for event_id, sequence, seat in (("c", 10, 0), ("d", 11, 1))
    ]
    reconciliations = [
        ActionAmountReconciliation(
            action_event_id=action.event_id,
            seat=action.seat,
            action="fold",
            amount_native=0,
            status="not_required",
            reason="test evidence",
        )
        for action in actions
    ]
    return _build(actions=actions, amount_reconciliations=reconciliations)


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
    assert first.state.hero_position is Position.BTN
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


def test_retains_last_validated_prefix_when_current_frame_is_not_ready() -> None:
    service = LiveObservationService()
    service._retained_canonical_hand = _build()

    status = service.status()

    assert status.canonical_hand is None
    assert status.retained_canonical_hand == _build()


def test_completes_exact_single_winner_settlement_at_next_boundary() -> None:
    prefix = _closed_prefix()
    increase = StackIncreaseCandidate(
        event_id="e" * 64,
        hand_epoch=1,
        frame_sequence=20,
        seat=2,
        previous_stack_native=98,
        current_stack_native=101,
        increase_native=3,
    )

    completed = complete_single_winner_live_hand(prefix, increase)

    assert completed.complete is True
    assert [event.type for event in completed.events[-2:]] == [
        "pot_awarded",
        "hand_completed",
    ]
    assert completed.state.pot_main_chips == 0
    assert completed.state.seats[2].stack_chips == 101

    service = LiveObservationService()
    service._retained_canonical_hand = prefix
    service._hand_epoch = 2
    service._hand_epoch_start_sequence = 21
    service._hand_boundary_validation = LiveHandBoundaryValidation(
        hand_epoch=2,
        previous_dealer_seat=0,
        current_dealer_seat=1,
        expected_dealer_seat=1,
        previous_active_seats=[0, 1, 2],
        current_active_seats=[0, 1, 2],
        status="validated",
        reason="test evidence",
    )
    service._stack_increases.append(increase)

    status = service.status()
    assert status.latest_completed_hand is not None
    assert status.latest_completed_hand.complete is True


def test_rejects_ambiguous_or_nonexact_settlement() -> None:
    prefix = _closed_prefix()
    increase = StackIncreaseCandidate(
        event_id="e" * 64,
        hand_epoch=1,
        frame_sequence=20,
        seat=2,
        previous_stack_native=98,
        current_stack_native=100,
        increase_native=2,
    )

    with pytest.raises(ValueError, match="complete retained pot"):
        complete_single_winner_live_hand(prefix, increase)
