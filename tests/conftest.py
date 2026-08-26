from decimal import Decimal
from uuid import UUID

import pytest

from xpoker_agent.models import Confidence, EventCategory, HandEvent, Position
from xpoker_agent.state import create_initial_state

TEST_HAND_ID = UUID("10000000-0000-0000-0000-000000000001")
CONFIDENCE = Confidence(score=1.0, calibration_id="test-v1")


def make_event(
    sequence: int, category: EventCategory, event_type: str, **kwargs: object
) -> HandEvent:
    return HandEvent(
        hand_id=TEST_HAND_ID,
        sequence=sequence,
        category=category,
        type=event_type,
        confidence=CONFIDENCE,
        **kwargs,
    )


def make_initial_state():
    return create_initial_state(
        hand_id=TEST_HAND_ID,
        config_version="game-9max-nlh-v1",
        hero_seat=6,
        occupied_stacks_chips={
            6: Decimal("100"),
            7: Decimal("100"),
            8: Decimal("100"),
        },
        positions={6: Position.BTN, 7: Position.SB, 8: Position.BB},
    )


@pytest.fixture
def initial_state():
    return make_initial_state()
