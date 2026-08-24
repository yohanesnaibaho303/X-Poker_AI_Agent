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
SIMULATED_CONFIDENCE = Confidence(
    score=1.0, calibration_id="deterministic-simulation-v1", stable_frames=1
)


def _event(sequence: int, category: EventCategory, event_type: str, **kwargs: object) -> HandEvent:
    return HandEvent(
        event_id=uuid5(NAMESPACE_URL, f"xpoker-agent:simulation:event:{sequence}"),
        hand_id=SIMULATED_HAND_ID,
        sequence=sequence,
        category=category,
        type=event_type,
        confidence=SIMULATED_CONFIDENCE,
        **kwargs,
    )


def simulated_events() -> list[HandEvent]:
    return [
        _event(1, EventCategory.LIFECYCLE, "hand_started"),
        _event(2, EventCategory.DEALING, "dealer_assigned", dealer_seat=6),
        _event(
            3,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=7,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("0.5"), added_bb=Decimal("0.5")),
        ),
        _event(
            4,
            EventCategory.FORCED_WAGER,
            "blind_posted",
            actor_seat=8,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("1"), added_bb=Decimal("1")),
        ),
        _event(
            5,
            EventCategory.DEALING,
            "hole_cards_observed",
            actor_seat=6,
            street=Street.PREFLOP,
            cards=["As", "Kd"],
        ),
        _event(
            6,
            EventCategory.BETTING_ACTION,
            "raise",
            actor_seat=6,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("2"), added_bb=Decimal("2")),
        ),
        _event(
            7,
            EventCategory.BETTING_ACTION,
            "fold",
            actor_seat=7,
            street=Street.PREFLOP,
        ),
        _event(
            8,
            EventCategory.BETTING_ACTION,
            "call",
            actor_seat=8,
            street=Street.PREFLOP,
            amount=EventAmount(to_bb=Decimal("2"), added_bb=Decimal("1")),
        ),
        _event(
            9,
            EventCategory.DEALING,
            "board_cards_observed",
            street=Street.FLOP,
            cards=["Qs", "Jh", "2c"],
        ),
        _event(
            10,
            EventCategory.BETTING_ACTION,
            "check",
            actor_seat=8,
            street=Street.FLOP,
        ),
        _event(
            11,
            EventCategory.BETTING_ACTION,
            "bet",
            actor_seat=6,
            street=Street.FLOP,
            amount=EventAmount(to_bb=Decimal("2.5"), added_bb=Decimal("2.5")),
        ),
        _event(
            12,
            EventCategory.BETTING_ACTION,
            "fold",
            actor_seat=8,
            street=Street.FLOP,
        ),
        _event(
            13,
            EventCategory.SETTLEMENT,
            "pot_awarded",
            winner_seat=6,
            street=Street.FLOP,
            amount=EventAmount(added_bb=Decimal("7")),
        ),
        _event(14, EventCategory.LIFECYCLE, "hand_completed", street=Street.FLOP),
    ]


def run_simulated_hand() -> tuple[list[HandState], list[HandEvent]]:
    config = load_game_config()
    state = create_initial_state(
        hand_id=SIMULATED_HAND_ID,
        config_version=config.config_id,
        hero_seat=6,
        occupied_stacks_bb={
            6: Decimal("100"),
            7: Decimal("100"),
            8: Decimal("100"),
        },
        positions={6: Position.BTN, 7: Position.SB, 8: Position.BB},
    )
    states = [state]
    reducer = HandStateReducer()
    events = simulated_events()
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
