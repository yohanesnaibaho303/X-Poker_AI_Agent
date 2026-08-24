from decimal import Decimal

from xpoker_agent.vision.blind_posts import reconcile_blind_posts
from xpoker_agent.vision.models import StackDeltaCandidate


def _delta(sequence: int, seat: int, amount: str) -> StackDeltaCandidate:
    value = Decimal(amount)
    return StackDeltaCandidate(
        event_id=f"{sequence:064x}",
        hand_epoch=3,
        frame_sequence=sequence,
        seat=seat,
        street="preflop",
        previous_stack_native=Decimal("100"),
        current_stack_native=Decimal("100") - value,
        committed_native=value,
    )


def test_matches_exact_blinds_clockwise_across_an_empty_seat() -> None:
    results = reconcile_blind_posts(
        hand_epoch=3,
        epoch_start_sequence=20,
        table_size=9,
        dealer_seat=1,
        active_seats=[0, 1, 2, 4, 6],
        small_blind_native=Decimal("1"),
        big_blind_native=Decimal("2"),
        stack_deltas=[_delta(22, 2, "1"), _delta(23, 4, "2")],
    )

    assert [(item.seat, item.blind_kind, item.status) for item in results] == [
        (2, "small_blind", "matched"),
        (4, "big_blind", "matched"),
    ]


def test_aggregated_big_blind_and_call_is_not_split_or_inferred() -> None:
    results = reconcile_blind_posts(
        hand_epoch=3,
        epoch_start_sequence=20,
        table_size=9,
        dealer_seat=1,
        active_seats=[0, 1, 2, 3, 4, 6],
        small_blind_native=Decimal("1"),
        big_blind_native=Decimal("2"),
        stack_deltas=[_delta(22, 2, "1"), _delta(25, 3, "4")],
    )

    assert results[0].status == "matched"
    assert results[1].status == "pending"
    assert results[1].stack_delta_event_id is None


def test_late_equal_delta_does_not_count_as_a_blind() -> None:
    results = reconcile_blind_posts(
        hand_epoch=3,
        epoch_start_sequence=20,
        table_size=9,
        dealer_seat=1,
        active_seats=[0, 1, 2, 3, 4, 6],
        small_blind_native=Decimal("1"),
        big_blind_native=Decimal("2"),
        stack_deltas=[_delta(29, 2, "1"), _delta(30, 3, "2")],
    )

    assert all(item.status == "pending" for item in results)
