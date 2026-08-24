import sqlite3
from decimal import Decimal

import pytest
from conftest import TEST_HAND_ID, make_event, make_initial_state

from xpoker_agent.models import (
    EventAmount,
    EventCategory,
    ParticipationStatus,
    Position,
    Street,
    TableStatus,
)
from xpoker_agent.reconstruction.pots import build_pot_layers
from xpoker_agent.reconstruction.replay import export_canonical_history, replay_events
from xpoker_agent.reconstruction.store import AppendOnlyEventStore, EventStoreError
from xpoker_agent.simulation import SIMULATED_HAND_ID, run_simulated_hand, simulated_events
from xpoker_agent.state import HandStateReducer, StateTransitionError, create_initial_state


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


def test_event_store_batch_is_atomic_on_invalid_sequence(tmp_path) -> None:
    events = [
        make_event(1, EventCategory.LIFECYCLE, "hand_started"),
        make_event(3, EventCategory.DEALING, "dealer_assigned", dealer_seat=6),
    ]
    with AppendOnlyEventStore(tmp_path / "hands.sqlite3") as store:
        with pytest.raises(EventStoreError, match="expected event sequence 2"):
            store.append_many(events)

        assert store.load_hand(TEST_HAND_ID) == []


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
        sum((seat.stack_bb for seat in result.seats), start=Decimal("0")) + result.pot_main_bb
    )
    assert reconstructed_total == Decimal("201.5")


def test_short_all_in_does_not_reopen_raise_for_player_who_already_acted() -> None:
    reducer, state = _preflop_after_blinds()
    state.seats[7].stack_bb = Decimal("3.5")
    state.seats[7].starting_stack_bb = Decimal("4")
    state.initial_total_chips_bb = Decimal("204")
    state = reducer.apply(
        state,
        make_event(
            5,
            EventCategory.BETTING_ACTION,
            "raise",
            actor_seat=6,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("3"), added_bb=Decimal("3")),
        ),
    )
    state = reducer.apply(
        state,
        make_event(
            6,
            EventCategory.BETTING_ACTION,
            "all_in",
            actor_seat=7,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("4"), added_bb=Decimal("3.5")),
        ),
    )
    state = reducer.apply(
        state,
        make_event(
            7,
            EventCategory.BETTING_ACTION,
            "call",
            actor_seat=8,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("4"), added_bb=Decimal("3")),
        ),
    )

    assert state.next_to_act_seat == 6
    assert state.raise_locked_seats == [6]
    with pytest.raises(StateTransitionError, match="not reopened"):
        reducer.apply(
            state,
            make_event(
                8,
                EventCategory.BETTING_ACTION,
                "raise",
                actor_seat=6,
                street=Street.PREFLOP,
                amount=EventAmount(to_bb=Decimal("6"), added_bb=Decimal("3")),
            ),
        )


def _multiway_all_in_state():
    state = create_initial_state(
        hand_id=TEST_HAND_ID,
        config_version="game-9max-nlh-v1",
        hero_seat=6,
        occupied_stacks_bb={6: Decimal("10"), 7: Decimal("30"), 8: Decimal("100")},
        positions={6: Position.BTN, 7: Position.SB, 8: Position.BB},
    )
    state = HandStateReducer().apply(state, make_event(1, EventCategory.LIFECYCLE, "hand_started"))
    for seat_number, commitment in ((6, Decimal("10")), (7, Decimal("30")), (8, Decimal("30"))):
        seat = state.seats[seat_number]
        seat.stack_bb -= commitment
        seat.committed_by_street_bb[Street.PREFLOP] = commitment
    state.seats[6].participation = ParticipationStatus.ALL_IN
    state.seats[7].participation = ParticipationStatus.ALL_IN
    object.__setattr__(state, "pot_main_bb", Decimal("70"))
    object.__setattr__(state, "pot_layers", build_pot_layers(state.seats))
    return state


def test_side_pots_are_built_from_all_in_caps_and_eligibility() -> None:
    state = _multiway_all_in_state()

    assert [(layer.amount_bb, layer.eligible_seats) for layer in state.pot_layers] == [
        (Decimal("30"), [6, 7, 8]),
        (Decimal("40"), [7, 8]),
    ]


def test_ineligible_player_cannot_win_side_pot() -> None:
    state = _multiway_all_in_state()

    with pytest.raises(StateTransitionError, match="not eligible"):
        HandStateReducer().apply(
            state,
            make_event(
                2,
                EventCategory.SETTLEMENT,
                "pot_awarded",
                winner_seat=6,
                pot_index=1,
                amount=EventAmount(added_bb=Decimal("40")),
            ),
        )


def test_side_and_split_main_pot_awards_conserve_all_chips() -> None:
    reducer = HandStateReducer()
    state = _multiway_all_in_state()
    awards = [
        (8, 1, Decimal("40")),
        (6, 0, Decimal("15")),
        (7, 0, Decimal("15")),
    ]
    for sequence, (winner, pot_index, amount) in enumerate(awards, start=2):
        state = reducer.apply(
            state,
            make_event(
                sequence,
                EventCategory.SETTLEMENT,
                "pot_awarded",
                winner_seat=winner,
                pot_index=pot_index,
                amount=EventAmount(added_bb=amount),
            ),
        )
    state = reducer.apply(
        state,
        make_event(5, EventCategory.LIFECYCLE, "hand_completed", street=Street.PREFLOP),
    )

    assert state.table_status is TableStatus.HAND_COMPLETE
    assert state.pot_main_bb == 0
    assert [layer.remaining_bb for layer in state.pot_layers] == [0, 0]
    assert sum((seat.stack_bb for seat in state.seats), start=Decimal("0")) == Decimal("140")


def test_invalid_replay_is_quarantined_at_last_valid_state() -> None:
    initial = make_initial_state()
    events = [
        make_event(1, EventCategory.LIFECYCLE, "hand_started"),
        make_event(2, EventCategory.DEALING, "dealer_assigned", dealer_seat=6),
        make_event(
            3,
            EventCategory.BETTING_ACTION,
            "check",
            actor_seat=6,
            street=Street.PREFLOP,
        ),
    ]

    result = replay_events(initial, events)

    assert result.accepted is False
    assert result.accepted_events == 2
    assert result.state.revision == 2
    assert result.failure is not None
    assert result.failure.failed_event_sequence == 3
    assert len(result.failure.event_payload_sha256) == 64


def test_canonical_history_export_is_byte_deterministic() -> None:
    states, events = run_simulated_hand()

    first = export_canonical_history(states[0], events, states[-1])
    second = export_canonical_history(states[0], events, states[-1])

    assert first == second
    assert first.endswith(b"\n")
