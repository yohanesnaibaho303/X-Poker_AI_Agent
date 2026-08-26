from decimal import Decimal
from uuid import uuid4

import pytest
from conftest import CONFIDENCE, TEST_HAND_ID
from pydantic import ValidationError

from xpoker_agent.models import (
    ComboStrategy,
    EventAmount,
    EventCategory,
    HandEvent,
    ParticipationStatus,
)


def test_event_category_rejects_mismatched_type() -> None:
    with pytest.raises(ValidationError, match="not valid for category"):
        HandEvent(
            hand_id=TEST_HAND_ID,
            sequence=1,
            category=EventCategory.BETTING_ACTION,
            type="hand_started",
            confidence=CONFIDENCE,
        )


def test_amount_action_requires_actor_and_positive_amount() -> None:
    with pytest.raises(ValidationError):
        HandEvent(
            hand_id=TEST_HAND_ID,
            sequence=1,
            category=EventCategory.BETTING_ACTION,
            type="raise",
            amount=EventAmount(added_chips=Decimal("0")),
            confidence=CONFIDENCE,
        )


def test_duplicate_or_invalid_cards_are_rejected() -> None:
    with pytest.raises(ValidationError):
        HandEvent(
            hand_id=TEST_HAND_ID,
            sequence=1,
            category=EventCategory.DEALING,
            type="hole_cards_observed",
            actor_seat=6,
            cards=["As", "As"],
            confidence=CONFIDENCE,
        )


def test_combo_action_frequencies_must_sum_to_one() -> None:
    with pytest.raises(ValidationError, match="sum to one"):
        ComboStrategy(weight=1.0, actions={"call": 0.4, "raise": 0.5})


def test_player_participation_is_separate_from_action_event() -> None:
    assert ParticipationStatus.SITTING_OUT.value == "sitting_out"
    event_categories = HandEvent.model_json_schema()["$defs"]["EventCategory"]["enum"]
    assert "sitting_out" not in event_categories


def test_unknown_schema_fields_fail_closed() -> None:
    payload = {
        "hand_id": str(uuid4()),
        "sequence": 1,
        "category": "lifecycle",
        "type": "hand_started",
        "confidence": {"score": 1, "calibration_id": "test"},
        "invented_field": True,
    }
    with pytest.raises(ValidationError, match="Extra inputs"):
        HandEvent.model_validate(payload)
