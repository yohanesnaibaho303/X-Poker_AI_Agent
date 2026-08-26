import json
from decimal import Decimal
from uuid import UUID

from conftest import CONFIDENCE

from xpoker_agent.models import EventAmount, EventCategory, HandEvent, Position, Street
from xpoker_agent.reconstruction.replay import persist_quarantine, replay_events
from xpoker_agent.reconstruction.session import validate_hand_boundary
from xpoker_agent.simulation import run_simulated_hand
from xpoker_agent.state import HandStateReducer, create_initial_state


def _event(hand_id: UUID, sequence: int, category: EventCategory, event_type: str, **kwargs):
    return HandEvent(
        hand_id=hand_id,
        sequence=sequence,
        category=category,
        type=event_type,
        confidence=CONFIDENCE,
        **kwargs,
    )


def _started_hand(hand_id: UUID, dealer_seat: int):
    state = create_initial_state(
        hand_id=hand_id,
        config_version="game-9max-nlh-v1",
        hero_seat=6,
        occupied_stacks_chips={6: Decimal("100"), 7: Decimal("100"), 8: Decimal("100")},
        positions={6: Position.BTN, 7: Position.SB, 8: Position.BB},
    )
    reducer = HandStateReducer()
    state = reducer.apply(state, _event(hand_id, 1, EventCategory.LIFECYCLE, "hand_started"))
    return reducer.apply(
        state,
        _event(
            hand_id,
            2,
            EventCategory.DEALING,
            "dealer_assigned",
            dealer_seat=dealer_seat,
        ),
    )


def test_next_hand_dealer_moves_clockwise_to_next_dealt_seat() -> None:
    states, _ = run_simulated_hand()
    current = _started_hand(UUID("20000000-0000-0000-0000-000000000002"), dealer_seat=7)

    result = validate_hand_boundary(states[-1], current)

    assert result.valid is True
    assert result.expected_dealer_seat == 7


def test_wrong_dealer_or_changed_seat_set_fails_closed() -> None:
    states, _ = run_simulated_hand()
    current = _started_hand(UUID("20000000-0000-0000-0000-000000000003"), dealer_seat=7)
    current.seats[7].starting_stack_chips = 0

    result = validate_hand_boundary(states[-1], current)

    assert result.valid is False
    assert "dealt_seat_set_changed" in result.issues
    assert "dealer_did_not_move_to_next_dealt_seat" in result.issues


def test_heads_up_action_order_is_button_first_preflop_and_other_seat_postflop() -> None:
    hand_id = UUID("20000000-0000-0000-0000-000000000004")
    state = create_initial_state(
        hand_id=hand_id,
        config_version="game-9max-nlh-v1",
        hero_seat=6,
        occupied_stacks_chips={6: Decimal("100"), 8: Decimal("100")},
        positions={6: Position.BTN, 8: Position.BB},
    )
    events = [
        _event(hand_id, 1, EventCategory.LIFECYCLE, "hand_started"),
        _event(hand_id, 2, EventCategory.DEALING, "dealer_assigned", dealer_seat=6),
        _event(
            hand_id,
            3,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=6,
            street=Street.PREFLOP,
            amount=EventAmount(to_chips=Decimal("0.5"), added_chips=Decimal("0.5")),
        ),
        _event(
            hand_id,
            4,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=8,
            street=Street.PREFLOP,
            amount=EventAmount(to_chips=Decimal("1"), added_chips=Decimal("1")),
        ),
    ]
    result = replay_events(state, events)
    assert result.accepted is True
    assert result.state.next_to_act_seat == 6
    reducer = HandStateReducer()
    state = result.state
    state = reducer.apply(
        state,
        _event(
            hand_id,
            5,
            EventCategory.BETTING_ACTION,
            "call",
            actor_seat=6,
            street=Street.PREFLOP,
            amount=EventAmount(to_chips=Decimal("1"), added_chips=Decimal("0.5")),
        ),
    )
    state = reducer.apply(
        state,
        _event(
            hand_id,
            6,
            EventCategory.BETTING_ACTION,
            "check",
            actor_seat=8,
            street=Street.PREFLOP,
        ),
    )
    state = reducer.apply(
        state,
        _event(
            hand_id,
            7,
            EventCategory.DEALING,
            "board_cards_observed",
            street=Street.FLOP,
            cards=["As", "Kd", "Qc"],
        ),
    )

    assert state.next_to_act_seat == 8


def test_failed_replay_persists_idempotent_quarantine_evidence(tmp_path) -> None:
    hand_id = UUID("20000000-0000-0000-0000-000000000005")
    initial = create_initial_state(
        hand_id=hand_id,
        config_version="game-9max-nlh-v1",
        hero_seat=6,
        occupied_stacks_chips={6: Decimal("100"), 8: Decimal("100")},
        positions={6: Position.BTN, 8: Position.BB},
    )
    result = replay_events(
        initial,
        [
            _event(hand_id, 1, EventCategory.LIFECYCLE, "hand_started"),
            _event(
                hand_id,
                2,
                EventCategory.BETTING_ACTION,
                "check",
                actor_seat=6,
                street=Street.PREFLOP,
            ),
        ],
    )

    first = persist_quarantine(result, tmp_path / "quarantine")
    second = persist_quarantine(result, tmp_path / "quarantine")

    assert first == second
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["accepted"] is False
    assert payload["failure"]["failed_event_sequence"] == 2
