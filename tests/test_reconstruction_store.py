import sqlite3
from decimal import Decimal

import pytest
from conftest import make_event, make_initial_state

from xpoker_agent.models import EventAmount, EventCategory, ParticipationStatus, Street
from xpoker_agent.reconstruction.store import AppendOnlyEventStore, EventStoreError
from xpoker_agent.simulation import SIMULATED_HAND_ID, run_simulated_hand, simulated_events
from xpoker_agent.state import HandStateReducer, StateTransitionError


def _preflop_after_blinds():
    reducer = HandStateReducer()
    state = reducer.apply(
        make_initial_state(), make_event(1, EventCategory.LIFECYCLE, "hand_started")
    )
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
            actor_seat=7,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("0.5"), added_bb=Decimal("0.5")),
        ),
    )
    state = reducer.apply(
        state,
        make_event(
            4,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=8,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("1"), added_bb=Decimal("1")),
        ),
    )
    return reducer, state


def test_event_store_round_trip_and_hash_chain(tmp_path) -> None:
    events = simulated_events()
    with AppendOnlyEventStore(tmp_path / "nested" / "hands.sqlite3") as store:
        hashes = store.append_many(events)

        assert len(hashes) == len(events)
        assert len(set(hashes)) == len(events)
        assert store.verify_hand(SIMULATED_HAND_ID) == []
        assert [event.model_dump(mode="json") for event in store.load_hand(SIMULATED_HAND_ID)] == [
            event.model_dump(mode="json") for event in events
        ]


def test_event_store_replay_reproduces_final_state(tmp_path) -> None:
    expected_states, events = run_simulated_hand()
    with AppendOnlyEventStore(tmp_path / "hands.sqlite3") as store:
        store.append_many(events)
        # Use the simulation's exact initial identity/configuration.
        replayed = expected_states[0]
        reducer = HandStateReducer()
        for event in store.load_hand(SIMULATED_HAND_ID):
            replayed = reducer.apply(replayed, event)

    assert replayed.model_dump(mode="json") == expected_states[-1].model_dump(mode="json")


def test_event_store_rejects_non_contiguous_sequence(tmp_path) -> None:
    with (
        AppendOnlyEventStore(tmp_path / "hands.sqlite3") as store,
        pytest.raises(EventStoreError, match="expected event sequence 1"),
    ):
        store.append(make_event(2, EventCategory.LIFECYCLE, "hand_started"))


def test_event_store_database_triggers_block_update_and_delete(tmp_path) -> None:
    with AppendOnlyEventStore(tmp_path / "hands.sqlite3") as store:
        store.append(make_event(1, EventCategory.LIFECYCLE, "hand_started"))
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            store._connection.execute(  # noqa: SLF001
                "UPDATE hand_events SET payload_json = '{}' WHERE sequence = 1"
            )
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            store._connection.execute(  # noqa: SLF001
                "DELETE FROM hand_events WHERE sequence = 1"
            )


def test_check_is_rejected_while_facing_blind() -> None:
    reducer, state = _preflop_after_blinds()

    with pytest.raises(StateTransitionError, match="cannot check"):
        reducer.apply(
            state,
            make_event(
                5,
                EventCategory.BETTING_ACTION,
                "check",
                actor_seat=6,
                street=Street.PREFLOP,
            ),
        )


def test_out_of_turn_action_is_rejected() -> None:
    reducer, state = _preflop_after_blinds()

    assert state.next_to_act_seat == 6
    with pytest.raises(StateTransitionError, match="out-of-turn"):
        reducer.apply(
            state,
            make_event(
                5,
                EventCategory.BETTING_ACTION,
                "fold",
                actor_seat=7,
                street=Street.PREFLOP,
            ),
        )


def test_board_cannot_advance_before_betting_round_closes() -> None:
    reducer, state = _preflop_after_blinds()

    with pytest.raises(StateTransitionError, match="round closes"):
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


def test_call_must_match_current_wager_exactly() -> None:
    reducer, state = _preflop_after_blinds()

    with pytest.raises(StateTransitionError, match="must match"):
        reducer.apply(
            state,
            make_event(
                5,
                EventCategory.BETTING_ACTION,
                "call",
                actor_seat=6,
                street=Street.PREFLOP,
                amount=EventAmount(to_bb=Decimal("0.5"), added_bb=Decimal("0.5")),
            ),
        )


def test_raise_must_meet_minimum_full_raise_increment() -> None:
    reducer, state = _preflop_after_blinds()

    with pytest.raises(StateTransitionError, match="minimum full-raise"):
        reducer.apply(
            state,
            make_event(
                5,
                EventCategory.BETTING_ACTION,
                "raise",
                actor_seat=6,
                street=Street.PREFLOP,
                amount=EventAmount(to_bb=Decimal("1.5"), added_bb=Decimal("1.5")),
            ),
        )


def test_short_all_in_raise_is_legal_but_does_not_lower_minimum_increment() -> None:
    reducer, state = _preflop_after_blinds()
    state.seats[6].stack_bb = Decimal("1.5")
    state.seats[6].starting_stack_bb = Decimal("1.5")
    state.initial_total_chips_bb = Decimal("201.5")

    result = reducer.apply(
        state,
        make_event(
            5,
            EventCategory.BETTING_ACTION,
            "all_in",
            actor_seat=6,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("1.5"), added_bb=Decimal("1.5")),
        ),
    )

    assert result.seats[6].participation is ParticipationStatus.ALL_IN
    assert result.current_bet_bb == Decimal("1.5")
    assert result.minimum_raise_increment_bb == Decimal("1")
    reconstructed_total = (
        sum((seat.stack_bb for seat in result.seats), start=Decimal("0"))
        + result.pot_main_bb
    )
    assert reconstructed_total == Decimal("201.5")
