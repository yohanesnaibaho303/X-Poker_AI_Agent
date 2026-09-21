import pytest

from xpoker_agent.models import Position
from xpoker_agent.vision.positions import assign_dealt_positions, assign_full_ring_positions


def test_nine_max_positions_follow_dealer_clockwise() -> None:
    positions = assign_full_ring_positions(table_size=9, dealer_seat=4, active_seats=set(range(9)))

    assert positions[4] is Position.BTN
    assert positions[5] is Position.SB
    assert positions[6] is Position.BB
    assert positions[7] is Position.UTG
    assert positions[3] is Position.CO


def test_six_max_layout_is_rejected() -> None:
    with pytest.raises(ValueError, match="only the 9-max"):
        assign_full_ring_positions(table_size=6, dealer_seat=0, active_seats=set(range(6)))


def test_partial_ring_never_silently_substitutes_position_set() -> None:
    with pytest.raises(ValueError, match="partial-ring"):
        assign_full_ring_positions(table_size=9, dealer_seat=4, active_seats=set(range(8)))


def test_seven_handed_positions_skip_empty_seats_without_switching_table_scope() -> None:
    positions = assign_dealt_positions(
        table_size=9,
        dealer_seat=6,
        active_seats={0, 2, 3, 4, 5, 6, 7},
    )

    assert positions == {
        6: Position.BTN,
        7: Position.SB,
        0: Position.BB,
        2: Position.UTG,
        3: Position.LJ,
        4: Position.HJ,
        5: Position.CO,
    }


def test_eight_handed_position_order_has_exactly_eight_positions() -> None:
    positions = assign_dealt_positions(
        table_size=9,
        dealer_seat=0,
        active_seats=set(range(8)),
    )

    assert list(positions.values()) == [
        Position.BTN,
        Position.SB,
        Position.BB,
        Position.UTG,
        Position.UTG_1,
        Position.LJ,
        Position.HJ,
        Position.CO,
    ]
