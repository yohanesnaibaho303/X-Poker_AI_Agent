"""Fail-closed seat-to-position assignment for fully dealt supported tables."""

from __future__ import annotations

from xpoker_agent.models import Position, positions_for_table_size


def assign_full_ring_positions(
    *, table_size: int, dealer_seat: int, active_seats: set[int]
) -> dict[int, Position]:
    expected = set(range(table_size))
    if active_seats != expected:
        raise ValueError(
            "position naming requires every configured seat to be actively dealt; "
            "partial-ring naming is intentionally unavailable"
        )
    if dealer_seat not in active_seats:
        raise ValueError("dealer seat must be actively dealt")
    clockwise = [(dealer_seat + offset) % table_size for offset in range(table_size)]
    assignments = {
        clockwise[0]: Position.BTN,
        clockwise[1]: Position.SB,
        clockwise[2]: Position.BB,
    }
    early_positions = [
        position
        for position in positions_for_table_size(table_size)
        if position not in {Position.BTN, Position.SB, Position.BB}
    ]
    for seat, position in zip(clockwise[3:], early_positions, strict=True):
        assignments[seat] = position
    return assignments
