import pytest

from xpoker_agent.models import Position
from xpoker_agent.vision.positions import assign_full_ring_positions


def test_nine_max_positions_follow_dealer_clockwise() -> None:
    positions = assign_full_ring_positions(
        table_size=9, dealer_seat=4, active_seats=set(range(9))
    )

    assert positions[4] is Position.BTN
    assert positions[5] is Position.SB
    assert positions[6] is Position.BB
    assert positions[7] is Position.UTG
    assert positions[3] is Position.CO


def test_six_max_positions_follow_dealer_clockwise() -> None:
    positions = assign_full_ring_positions(
        table_size=6, dealer_seat=0, active_seats=set(range(6))
    )

    assert positions == {
        0: Position.BTN,
        1: Position.SB,
        2: Position.BB,
        3: Position.UTG,
        4: Position.HJ,
        5: Position.CO,
    }


def test_partial_ring_never_silently_substitutes_position_set() -> None:
    with pytest.raises(ValueError, match="partial-ring"):
        assign_full_ring_positions(table_size=9, dealer_seat=4, active_seats=set(range(8)))
