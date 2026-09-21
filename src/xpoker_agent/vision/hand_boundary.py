"""Fail-closed live dealer/seat validation at provisional hand boundaries."""

from __future__ import annotations

from xpoker_agent.vision.models import LiveHandBoundaryValidation


def validate_live_hand_boundary(
    *,
    hand_epoch: int,
    table_size: int,
    previous_dealer_seat: int | None,
    current_dealer_seat: int | None,
    previous_active_seats: list[int],
    current_active_seats: list[int],
) -> LiveHandBoundaryValidation:
    if table_size != 9:
        raise ValueError("only the 9-max table layout is supported")
    previous = set(previous_active_seats)
    current = set(current_active_seats)
    issues: list[str] = []
    if previous_dealer_seat is None or not previous:
        issues.append("prior_hand_context_unavailable")
    if current_dealer_seat is None or not current:
        issues.append("current_hand_context_unresolved")
    if previous and current and previous != current:
        issues.append("active_seat_set_changed")
    expected: int | None = None
    if previous_dealer_seat is not None and previous == current and current:
        for offset in range(1, table_size + 1):
            candidate = (previous_dealer_seat + offset) % table_size
            if candidate in current:
                expected = candidate
                break
    if previous_dealer_seat is not None and current_dealer_seat == previous_dealer_seat:
        issues.append("dealer_not_advanced_yet")
    elif (
        expected is not None and current_dealer_seat is not None and current_dealer_seat != expected
    ):
        issues.append("dealer_did_not_move_to_next_dealt_seat")

    rejected = any(
        issue in {"active_seat_set_changed", "dealer_did_not_move_to_next_dealt_seat"}
        for issue in issues
    )
    status = "rejected" if rejected else ("validated" if not issues else "pending")
    return LiveHandBoundaryValidation(
        hand_epoch=hand_epoch,
        previous_dealer_seat=previous_dealer_seat,
        current_dealer_seat=current_dealer_seat,
        expected_dealer_seat=expected,
        previous_active_seats=sorted(previous),
        current_active_seats=sorted(current),
        status=status,
        issues=issues,
        reason=(
            "dealer advanced to the next unchanged dealt seat"
            if status == "validated"
            else "live hand boundary remains ineligible for canonical reconstruction"
        ),
    )
