from decimal import Decimal

from xpoker_agent.models import EventCategory, Position
from xpoker_agent.simulation import run_simulated_hand


def test_native_blinds_are_forced_wagers_before_first_opening_raise() -> None:
    _, events = run_simulated_hand()

    small_blind, big_blind, opening_raise = events[2], events[3], events[5]
    assert small_blind.category is EventCategory.FORCED_WAGER
    assert small_blind.type == "blind_posted"
    assert small_blind.amount is not None
    assert small_blind.amount.to_chips == Decimal("1")
    assert big_blind.category is EventCategory.FORCED_WAGER
    assert big_blind.type == "blind_posted"
    assert big_blind.amount is not None
    assert big_blind.amount.to_chips == Decimal("2")
    assert opening_raise.category is EventCategory.BETTING_ACTION
    assert opening_raise.type == "raise"
    assert opening_raise.amount is not None
    assert opening_raise.amount.to_chips == Decimal("4")


def test_simulated_hand_retains_nine_canonical_seats_and_positions() -> None:
    states, _ = run_simulated_hand()
    initial = states[0]

    assert initial.table_size == 9
    assert len(initial.seats) == 9
    assert initial.seats[6].position is Position.BTN
    assert initial.seats[7].position is Position.SB
    assert initial.seats[8].position is Position.BB
