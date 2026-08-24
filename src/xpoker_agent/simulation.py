"""Deterministic end-to-end simulated NLH hand used by tests and development."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from xpoker_agent.config import load_game_config
from xpoker_agent.models import (
    Confidence,
    EventAmount,
    EventCategory,
    HandEvent,
    HandState,
    Position,
    Street,
)
from xpoker_agent.state import HandStateReducer, create_initial_state

SIMULATED_HAND_ID = UUID("00000000-0000-0000-0000-000000000001")
SIMULATED_6MAX_HAND_ID = UUID("00000000-0000-0000-0000-000000000006")
SIMULATED_CONFIDENCE = Confidence(
    score=1.0, calibration_id="deterministic-simulation-v1", stable_frames=1
)


def _event(
    table_size: int,
    hand_id: UUID,
    sequence: int,
    category: EventCategory,
    event_type: str,
    **kwargs: object,
) -> HandEvent:
    return HandEvent(
        event_id=uuid5(NAMESPACE_URL, f"xpoker-agent:simulation:{table_size}max:event:{sequence}"),
        hand_id=hand_id,
        sequence=sequence,
        category=category,
        type=event_type,
        confidence=SIMULATED_CONFIDENCE,
        **kwargs,
    )


def simulated_events(table_size: int = 9) -> list[HandEvent]:
    if table_size not in {6, 9}:
        raise ValueError("table_size must be 6 or 9")
    hand_id = SIMULATED_6MAX_HAND_ID if table_size == 6 else SIMULATED_HAND_ID
    hero, small_blind, big_blind = table_size - 3, table_size - 2, table_size - 1
    return [
        _event(table_size, hand_id, 1, EventCategory.LIFECYCLE, "hand_started"),
        _event(
            table_size,
            hand_id,
            2,
            EventCategory.DEALING,
            "dealer_assigned",
            dealer_seat=hero,
        ),
        _event(
            table_size,
            hand_id,
            3,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=small_blind,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("0.5"), added_bb=Decimal("0.5")),
        ),
        _event(
            table_size,
            hand_id,
            4,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=big_blind,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("1"), added_bb=Decimal("1")),
        ),
        _event(
            table_size,
            hand_id,
            5,
            EventCategory.DEALING,
            "hole_cards_observed",
            actor_seat=hero,
            street=Street.PREFLOP,
            cards=["As", "Kd"],
        ),
        _event(
            table_size,
            hand_id,
            6,
            EventCategory.BETTING_ACTION,
            "raise",
            actor_seat=hero,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("2"), added_bb=Decimal("2")),
        ),
        _event(
            table_size,
            hand_id,
            7,
            EventCategory.BETTING_ACTION,
            "fold",
            actor_seat=small_blind,
            street=Street.PREFLOP,
        ),
        _event(
            table_size,
            hand_id,
            8,
            EventCategory.BETTING_ACTION,
            "call",
            actor_seat=big_blind,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("2"), added_bb=Decimal("1")),
        ),
        _event(
            table_size,
            hand_id,
            9,
            EventCategory.DEALING,
            "board_cards_observed",
            street=Street.FLOP,
            cards=["Qs", "Jh", "2c"],
        ),
        _event(
            table_size,
            hand_id,
            10,
            EventCategory.BETTING_ACTION,
            "check",
            actor_seat=big_blind,
            street=Street.FLOP,
        ),
        _event(
            table_size,
            hand_id,
            11,
            EventCategory.BETTING_ACTION,
            "bet",
            actor_seat=hero,
            street=Street.FLOP,
            amount=EventAmount(to_bb=Decimal("2.5"), added_bb=Decimal("2.5")),
        ),
        _event(
            table_size,
            hand_id,
            12,
            EventCategory.BETTING_ACTION,
            "fold",
            actor_seat=big_blind,
            street=Street.FLOP,
        ),
        _event(
            table_size,
            hand_id,
            13,
            EventCategory.SETTLEMENT,
            "pot_awarded",
            winner_seat=hero,
            pot_index=0,
            street=Street.FLOP,
            amount=EventAmount(added_bb=Decimal("7")),
        ),
        _event(
            table_size,
            hand_id,
            14,
            EventCategory.LIFECYCLE,
            "hand_completed",
            street=Street.FLOP,
        ),
    ]


def run_simulated_hand(table_size: int = 9) -> tuple[list[HandState], list[HandEvent]]:
    config = load_game_config(table_size=table_size)
    hand_id = SIMULATED_6MAX_HAND_ID if table_size == 6 else SIMULATED_HAND_ID
    hero, small_blind, big_blind = table_size - 3, table_size - 2, table_size - 1
    state = create_initial_state(
        hand_id=hand_id,
        config_version=config.config_id,
        hero_seat=hero,
        occupied_stacks_bb={
            hero: Decimal("100"),
            small_blind: Decimal("100"),
            big_blind: Decimal("100"),
        },
        positions={hero: Position.BTN, small_blind: Position.SB, big_blind: Position.BB},
        table_size=table_size,
    )
    states = [state]
    reducer = HandStateReducer()
    events = simulated_events(table_size)
    for event in events:
        state = reducer.apply(state, event)
        states.append(state)
    return states, events


def main() -> None:
    states, events = run_simulated_hand()
    result = {
        "event_count": len(events),
        "initial_state": states[0].model_dump(mode="json"),
        "final_state": states[-1].model_dump(mode="json"),
    }
    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    main()
