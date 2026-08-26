"""Fail-closed seat-to-position assignment for supported dealt-player counts."""

from __future__ import annotations

from xpoker_agent.models import Position, positions_for_table_size

_DEALT_POSITIONS: dict[int, list[Position]] = {
    3: [Position.BTN, Position.SB, Position.BB],
    4: [Position.CO, Position.BTN, Position.SB, Position.BB],
    5: [Position.HJ, Position.CO, Position.BTN, Position.SB, Position.BB],
    6: [Position.UTG, Position.HJ, Position.CO, Position.BTN, Position.SB, Position.BB],
    7: [
        Position.UTG, Position.LJ, Position.HJ, Position.CO,
        Position.BTN, Position.SB, Position.BB,
    ],
    8: [
        Position.UTG, Position.UTG_1, Position.UTG_2, Position.LJ, Position.HJ,
        Position.CO, Position.BTN, Position.SB, Position.BB,
    ],
    9: list(positions_for_table_size(9)),
}


def assign_dealt_positions(
    *, table_size: int, dealer_seat: int, active_seats: set[int]
) -> dict[int, Position]:
    if table_size not in {6, 9}:
        raise ValueError("table_size must be 6 or 9")
    if not active_seats.issubset(range(table_size)):
        raise ValueError("active seats must fit the configured table")
    if dealer_seat not in active_seats:
        raise ValueError("dealer seat must be actively dealt")
    position_order = _DEALT_POSITIONS.get(len(active_seats))
    if position_order is None or len(active_seats) > table_size:
        raise ValueError("position naming requires between three and table_size dealt players")
    clockwise = [
        (dealer_seat + offset) % table_size
        for offset in range(table_size)
        if (dealer_seat + offset) % table_size in active_seats
    ]
    assignments = {
        clockwise[0]: Position.BTN,
        clockwise[1]: Position.SB,
        clockwise[2]: Position.BB,
    }
    for seat, position in zip(clockwise[3:], position_order[:-3], strict=True):
        assignments[seat] = position
    return assignments


def assign_full_ring_positions(
    *, table_size: int, dealer_seat: int, active_seats: set[int]
) -> dict[int, Position]:
    expected = set(range(table_size))
    if active_seats != expected:
        raise ValueError(
            "position naming requires every configured seat to be actively dealt; "
            "partial-ring naming is intentionally unavailable"
        )
    return assign_dealt_positions(
        table_size=table_size,
        dealer_seat=dealer_seat,
        active_seats=active_seats,
    )
