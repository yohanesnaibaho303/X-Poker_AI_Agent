from decimal import Decimal

import pytest
from conftest import make_event, make_initial_state
from hypothesis import given
from hypothesis import strategies as st

from xpoker_agent.models import EventAmount, EventCategory, ParticipationStatus, Street, TableStatus
from xpoker_agent.simulation import run_simulated_hand
from xpoker_agent.state import HandStateReducer, StateTransitionError


def test_simulated_hand_reconstructs_end_to_end() -> None:
    states, events = run_simulated_hand()
    final = states[-1]

    assert len(events) == 14
    assert len(states) == 15
    assert states[0].table_status is TableStatus.WAITING_FOR_HAND
    assert final.table_status is TableStatus.HAND_COMPLETE
    assert final.street is Street.FLOP
    assert final.board == ["Qs", "Jh", "2c"]
    assert final.hero_cards == ["As", "Kd"]
    assert final.pot_main_bb == 0
    assert final.seats[6].stack_bb == Decimal("102.5")
    assert final.seats[7].stack_bb == Decimal("99.5")
    assert final.seats[8].stack_bb == Decimal("98")
    assert final.seats[7].participation is ParticipationStatus.FOLDED
    assert final.seats[8].participation is ParticipationStatus.FOLDED


def test_simulated_hand_is_reproducible() -> None:
    first_states, first_events = run_simulated_hand()
    second_states, second_events = run_simulated_hand()

    assert [state.model_dump(mode="json") for state in first_states] == [
        state.model_dump(mode="json") for state in second_states
    ]
    assert [event.model_dump(mode="json") for event in first_events] == [
        event.model_dump(mode="json") for event in second_events
    ]


def test_reducer_does_not_mutate_previous_state(initial_state) -> None:
    next_state = HandStateReducer().apply(
        initial_state, make_event(1, EventCategory.LIFECYCLE, "hand_started")
    )

    assert initial_state.table_status is TableStatus.WAITING_FOR_HAND
    assert initial_state.revision == 0
    assert next_state.table_status is TableStatus.IN_HAND
    assert next_state.revision == 1


def test_event_sequence_must_be_contiguous(initial_state) -> None:
    with pytest.raises(StateTransitionError, match="expected event sequence 1"):
        HandStateReducer().apply(
            initial_state, make_event(2, EventCategory.LIFECYCLE, "hand_started")
        )


def test_hand_cannot_complete_with_unawarded_pot(initial_state) -> None:
    reducer = HandStateReducer()
    state = reducer.apply(initial_state, make_event(1, EventCategory.LIFECYCLE, "hand_started"))
    state = reducer.apply(
        state,
        make_event(
            2,
            EventCategory.DEALING,
            "dealer_assigned",
            dealer_seat=6,
        ),
    )
    state = reducer.apply(
        state,
        make_event(
            3,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=8,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("1"), added_bb=Decimal("1")),
        ),
    )

    with pytest.raises(StateTransitionError, match="fully awarded"):
        reducer.apply(state, make_event(4, EventCategory.LIFECYCLE, "hand_completed"))


@given(st.integers(min_value=1, max_value=10_000))
def test_posted_blind_conserves_chips(units: int) -> None:
    initial_state = make_initial_state()
    amount = Decimal(units) / Decimal("100")
    initial_state.seats[8].stack_bb = amount
    initial_state.seats[8].starting_stack_bb = amount
    initial_state.initial_total_chips_bb = amount + Decimal("200")
    reducer = HandStateReducer()
    state = reducer.apply(initial_state, make_event(1, EventCategory.LIFECYCLE, "hand_started"))
    state = reducer.apply(
        state,
        make_event(
            2,
            EventCategory.DEALING,
            "dealer_assigned",
            dealer_seat=6,
        ),
    )
    state = reducer.apply(
        state,
        make_event(
            3,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=8,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=amount, added_bb=amount),
        ),
    )

    assert state.seats[8].stack_bb == 0
    assert state.pot_main_bb == amount
    assert state.seats[8].stack_bb + state.pot_main_bb == amount


def test_known_card_cannot_reappear_on_board(initial_state) -> None:
    reducer = HandStateReducer()
    state = reducer.apply(initial_state, make_event(1, EventCategory.LIFECYCLE, "hand_started"))
    state = reducer.apply(
        state,
        make_event(
            2,
            EventCategory.DEALING,
            "hole_cards_observed",
            actor_seat=6,
            street=Street.PREFLOP,
            cards=["As", "Kd"],
        ),
    )

    with pytest.raises(StateTransitionError, match="duplicate"):
        reducer.apply(
            state,
            make_event(
                3,
                EventCategory.DEALING,
                "board_cards_observed",
                street=Street.FLOP,
                cards=["As", "Jh", "2c"],
            ),
        )
