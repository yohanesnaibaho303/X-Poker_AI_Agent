"""Fail-closed hand-boundary and dealer-movement validation."""

from __future__ import annotations

from pydantic import Field

from xpoker_agent.models import HandState, ParticipationStatus, StrictModel, TableStatus

_DEALT_STATUSES = {
    ParticipationStatus.SEATED,
    ParticipationStatus.ACTIVE,
    ParticipationStatus.FOLDED,
    ParticipationStatus.ALL_IN,
}


class HandBoundaryValidation(StrictModel):
    valid: bool
    expected_dealer_seat: int | None = Field(default=None, ge=0, le=8)
    observed_dealer_seat: int | None = Field(default=None, ge=0, le=8)
    issues: list[str]
    policy_id: str = "next-dealt-seat-clockwise-v1"


def _dealt_seats(state: HandState) -> set[int]:
    return {
        seat.seat
        for seat in state.seats
        if seat.starting_stack_bb > 0 and seat.participation in _DEALT_STATUSES
    }


def validate_hand_boundary(
    previous_final: HandState, current_started: HandState
) -> HandBoundaryValidation:
    issues: list[str] = []
    if previous_final.table_status is not TableStatus.HAND_COMPLETE:
        issues.append("previous_hand_not_complete")
    if current_started.table_status is not TableStatus.IN_HAND:
        issues.append("current_hand_not_started")
    if previous_final.hand_id == current_started.hand_id:
        issues.append("hand_identity_not_rotated")
    if previous_final.config_version != current_started.config_version:
        issues.append("configuration_changed")
    previous_dealt = _dealt_seats(previous_final)
    current_dealt = _dealt_seats(current_started)
    if previous_dealt != current_dealt:
        issues.append("dealt_seat_set_changed")
    expected: int | None = None
    if previous_final.dealer_seat is None:
        issues.append("previous_dealer_unknown")
    elif current_dealt:
        for offset in range(1, 10):
            candidate = (previous_final.dealer_seat + offset) % 9
            if candidate in current_dealt:
                expected = candidate
                break
    if current_started.dealer_seat is None:
        issues.append("current_dealer_unknown")
    elif expected is not None and current_started.dealer_seat != expected:
        issues.append("dealer_did_not_move_to_next_dealt_seat")
    return HandBoundaryValidation(
        valid=not issues,
        expected_dealer_seat=expected,
        observed_dealer_seat=current_started.dealer_seat,
        issues=issues,
    )
