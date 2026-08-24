"""Fail-closed event replay, quarantine records, and canonical history export."""

from __future__ import annotations

import hashlib
import json

from pydantic import Field

from xpoker_agent.models import HandEvent, HandState, StrictModel
from xpoker_agent.state import HandStateReducer, StateTransitionError


class ReconstructionFailure(StrictModel):
    hand_id: str
    failed_event_sequence: int = Field(ge=1)
    last_valid_revision: int = Field(ge=0)
    reason: str
    event_payload_sha256: str = Field(min_length=64, max_length=64)


class ReplayResult(StrictModel):
    accepted: bool
    state: HandState
    accepted_events: int = Field(ge=0)
    failure: ReconstructionFailure | None = None


def _event_payload(event: HandEvent) -> str:
    return json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def replay_events(initial_state: HandState, events: list[HandEvent]) -> ReplayResult:
    state = initial_state
    reducer = HandStateReducer()
    for accepted_events, event in enumerate(events):
        try:
            state = reducer.apply(state, event)
        except StateTransitionError as error:
            payload_hash = hashlib.sha256(_event_payload(event).encode()).hexdigest()
            return ReplayResult(
                accepted=False,
                state=state,
                accepted_events=accepted_events,
                failure=ReconstructionFailure(
                    hand_id=str(initial_state.hand_id),
                    failed_event_sequence=event.sequence,
                    last_valid_revision=state.revision,
                    reason=str(error),
                    event_payload_sha256=payload_hash,
                ),
            )
    return ReplayResult(
        accepted=True,
        state=state,
        accepted_events=len(events),
    )


def export_canonical_history(
    initial_state: HandState, events: list[HandEvent], final_state: HandState
) -> bytes:
    if initial_state.hand_id != final_state.hand_id or any(
        event.hand_id != initial_state.hand_id for event in events
    ):
        raise ValueError("canonical history must contain exactly one hand identity")
    payload = {
        "schema_version": "1.0",
        "hand_id": str(initial_state.hand_id),
        "config_version": initial_state.config_version,
        "initial_state": initial_state.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in events],
        "final_state": final_state.model_dump(mode="json"),
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
