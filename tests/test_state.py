from decimal import Decimal

import pytest
from conftest import make_event, make_initial_state
from hypothesis import given
from hypothesis import strategies as st

from xpoker_agent.models import (
    EventAmount,
    EventCategory,
    HandMode,
    ParticipationStatus,
    Position,
    Street,
    TableStatus,
)
from xpoker_agent.simulation import run_simulated_hand
from xpoker_agent.state import HandStateReducer, StateTransitionError, create_initial_state


def build_bomb_pot_flop_state():
    reducer = HandStateReducer()
    state = make_initial_state()
    state = reducer.apply(
        state,
        make_event(
            1,
            EventCategory.LIFECYCLE,
            "hand_started",
            hand_mode=HandMode.SINGLE_BOARD_BOMB_POT,
        ),
    )
    state = reducer.apply(
        state,
        make_event(2, EventCategory.DEALING, "dealer_assigned", dealer_seat=6),
    )
    for sequence, seat in enumerate((6, 7, 8), start=3):
        state = reducer.apply(
            state,
            make_event(
                sequence,
                EventCategory.FORCED_WAGER,
                "bomb_ante_posted",
                actor_seat=seat,
                street=Street.PREFLOP,
                amount=EventAmount(to_bb=Decimal("2"), added_bb=Decimal("2")),
            ),
        )
    state = reducer.apply(
        state,
        make_event(
            6,
            EventCategory.DEALING,
            "board_cards_observed",
            street=Street.FLOP,
            cards=["Qs", "Jh", "2c"],
        ),
    )
    return reducer, state


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


def test_single_board_bomb_pot_skips_preflop_and_begins_action_on_flop() -> None:
    reducer, state = build_bomb_pot_flop_state()

    assert state.hand_mode is HandMode.SINGLE_BOARD_BOMB_POT
    assert state.street is Street.FLOP
    assert state.pot_main_bb == Decimal("6")
    assert state.current_bet_bb == 0
    assert state.next_to_act_seat == 7

    state = reducer.apply(
        state,
        make_event(
            7,
            EventCategory.BETTING_ACTION,
            "check",
            actor_seat=7,
            street=Street.FLOP,
        ),
    )
    assert state.next_to_act_seat == 8


def test_bomb_pot_rejects_preflop_betting_and_blinds() -> None:
    reducer = HandStateReducer()
    state = reducer.apply(
        make_initial_state(),
        make_event(
            1,
            EventCategory.LIFECYCLE,
            "hand_started",
            hand_mode=HandMode.SINGLE_BOARD_BOMB_POT,
        ),
    )
    state = reducer.apply(
        state, make_event(2, EventCategory.DEALING, "dealer_assigned", dealer_seat=6)
    )

    with pytest.raises(StateTransitionError, match="blinds are invalid"):
        reducer.apply(
            state,
            make_event(
                3,
                EventCategory.FORCED_WAGER,
                "blind_posted",
                actor_seat=7,
                street=Street.PREFLOP,
                amount=EventAmount(to_bb=Decimal("1"), added_bb=Decimal("1")),
            ),
        )

    state = reducer.apply(
        state,
        make_event(
            3,
            EventCategory.FORCED_WAGER,
            "bomb_ante_posted",
            actor_seat=6,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("2"), added_bb=Decimal("2")),
        ),
    )
    with pytest.raises(StateTransitionError, match="no preflop betting"):
        reducer.apply(
            state,
            make_event(
                4,
                EventCategory.BETTING_ACTION,
                "fold",
                actor_seat=6,
                street=Street.PREFLOP,
            ),
        )


def test_bomb_pot_flop_requires_observed_contribution_from_every_participant() -> None:
    reducer = HandStateReducer()
    state = reducer.apply(
        make_initial_state(),
        make_event(
            1,
            EventCategory.LIFECYCLE,
            "hand_started",
            hand_mode=HandMode.SINGLE_BOARD_BOMB_POT,
        ),
    )
    state = reducer.apply(
        state, make_event(2, EventCategory.DEALING, "dealer_assigned", dealer_seat=6)
    )
    for sequence, seat in ((3, 6), (4, 7)):
        state = reducer.apply(
            state,
            make_event(
                sequence,
                EventCategory.FORCED_WAGER,
                "bomb_ante_posted",
                actor_seat=seat,
                street=Street.PREFLOP,
                amount=EventAmount(to_bb=Decimal("2"), added_bb=Decimal("2")),
            ),
        )

    with pytest.raises(StateTransitionError, match="every participant"):
        reducer.apply(
            state,
            make_event(
                5,
                EventCategory.DEALING,
                "board_cards_observed",
                street=Street.FLOP,
                cards=["Qs", "Jh", "2c"],
            ),
        )


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


def test_six_max_state_uses_six_slots_and_wraps_action_clockwise() -> None:
    state = create_initial_state(
        hand_id=make_event(1, EventCategory.LIFECYCLE, "hand_started").hand_id,
        config_version="game-6max-nlh-v1",
        hero_seat=3,
        occupied_stacks_bb={
            3: Decimal("100"),
            4: Decimal("100"),
            5: Decimal("100"),
        },
        positions={3: Position.BTN, 4: Position.SB, 5: Position.BB},
        table_size=6,
    )
    reducer = HandStateReducer()
    state = reducer.apply(state, make_event(1, EventCategory.LIFECYCLE, "hand_started"))
    state = reducer.apply(
        state,
        make_event(2, EventCategory.DEALING, "dealer_assigned", dealer_seat=3),
    )
    state = reducer.apply(
        state,
        make_event(
            3,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=5,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("1"), added_bb=Decimal("1")),
        ),
    )

    assert state.table_size == 6
    assert len(state.seats) == 6
    assert state.next_to_act_seat == 3


def test_six_max_state_rejects_nine_max_only_position() -> None:
    with pytest.raises(ValueError, match="invalid for the configured table size"):
        create_initial_state(
            hand_id=make_event(1, EventCategory.LIFECYCLE, "hand_started").hand_id,
            config_version="game-6max-nlh-v1",
            hero_seat=0,
            occupied_stacks_bb={0: Decimal("100")},
            positions={0: Position.LJ},
            table_size=6,
        )
