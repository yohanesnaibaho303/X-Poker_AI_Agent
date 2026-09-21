"""Fail-closed reconciliation of forced blind posts from early stack evidence."""

from __future__ import annotations

from decimal import Decimal

from xpoker_agent.vision.models import (
    BlindPostReconciliation,
    SeatBadgeAmountCandidate,
    StackDeltaCandidate,
)


def _next_active_after(seat: int, active: set[int], table_size: int) -> int | None:
    for offset in range(1, table_size + 1):
        candidate = (seat + offset) % table_size
        if candidate in active:
            return candidate
    return None


def reconcile_blind_posts(
    *,
    hand_epoch: int,
    epoch_start_sequence: int,
    table_size: int,
    dealer_seat: int,
    active_seats: list[int],
    small_blind_native: Decimal,
    big_blind_native: Decimal,
    stack_deltas: list[StackDeltaCandidate],
    badge_amounts: list[SeatBadgeAmountCandidate] | None = None,
    maximum_frame_offset: int = 12,
) -> list[BlindPostReconciliation]:
    """Match exact SB/BB decreases near a validated boundary; never infer a split."""
    active = set(active_seats)
    if dealer_seat not in active or len(active) < 3:
        return []
    small_blind_seat = _next_active_after(dealer_seat, active, table_size)
    big_blind_seat = (
        _next_active_after(small_blind_seat, active, table_size)
        if small_blind_seat is not None
        else None
    )
    if small_blind_seat is None or big_blind_seat is None:
        return []

    results: list[BlindPostReconciliation] = []
    badge_amounts = badge_amounts or []
    for kind, seat, amount in (
        ("small_blind", small_blind_seat, small_blind_native),
        ("big_blind", big_blind_seat, big_blind_native),
    ):
        matches = [
            delta
            for delta in stack_deltas
            if delta.hand_epoch == hand_epoch
            and delta.seat == seat
            and delta.street == "preflop"
            and delta.committed_native == amount
            and epoch_start_sequence <= delta.frame_sequence
            and delta.frame_sequence <= epoch_start_sequence + maximum_frame_offset
        ]
        badge_matches = [
            candidate
            for candidate in badge_amounts
            if candidate.hand_epoch == hand_epoch
            and candidate.seat == seat
            and candidate.amount_native == amount
            and epoch_start_sequence <= candidate.frame_sequence
            and candidate.frame_sequence <= epoch_start_sequence + maximum_frame_offset
        ]
        if len(matches) <= 1 and len(badge_matches) <= 1 and (matches or badge_matches):
            results.append(
                BlindPostReconciliation(
                    hand_epoch=hand_epoch,
                    seat=seat,
                    blind_kind=kind,
                    amount_native=amount,
                    stack_delta_event_id=matches[0].event_id if matches else None,
                    badge_amount_event_id=(badge_matches[0].event_id if badge_matches else None),
                    status="matched",
                    reason=(
                        "corroborating exact stack decrease and numeric badge at "
                        "expected blind seat"
                        if matches and badge_matches
                        else (
                            "exact early-epoch stack decrease at expected blind seat"
                            if matches
                            else "exact temporal numeric badge at expected blind seat"
                        )
                    ),
                )
            )
        else:
            results.append(
                BlindPostReconciliation(
                    hand_epoch=hand_epoch,
                    seat=seat,
                    blind_kind=kind,
                    amount_native=amount,
                    status=(
                        "ambiguous" if len(matches) > 1 or len(badge_matches) > 1 else "pending"
                    ),
                    reason=(
                        "multiple exact early-epoch evidence candidates at expected blind seat"
                        if len(matches) > 1 or len(badge_matches) > 1
                        else "exact early-epoch blind evidence not observed"
                    ),
                )
            )
    return results
