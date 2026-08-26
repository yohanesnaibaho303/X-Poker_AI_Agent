"""Typed local monitoring stream contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from xpoker_agent.models import HandEvent, HandState, StrictModel


class MonitorHealth(StrictModel):
    status: Literal["ok", "degraded", "stopped"]
    mode: Literal["observe", "analyze", "recommend"] = "observe"
    capture_active: bool = False
    controller_enabled: Literal[False] = False
    strategy_status: Literal["exact", "abstracted", "unavailable"] = "unavailable"
    warnings: list[str] = Field(default_factory=list)


class MonitorMetrics(StrictModel):
    frames_processed: int = Field(default=0, ge=0)
    state_revision: int = Field(default=0, ge=0)
    event_count: int = Field(default=0, ge=0)
    stream_sequence: int = Field(default=0, ge=0)
    dropped_deliveries: int = Field(default=0, ge=0)
    processing_latency_ms: float = Field(default=0, ge=0)


class ReplayProgress(StrictModel):
    active: bool = False
    index: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)
    interval_ms: int = Field(default=250, ge=25, le=5000)


class PokerMathSnapshot(StrictModel):
    effective_stack_chips: Decimal | None = Field(default=None, ge=0)
    call_amount_chips: Decimal = Field(default=Decimal("0"), ge=0)
    pot_odds_required_equity: Decimal | None = Field(default=None, ge=0, le=1)
    spr: Decimal | None = Field(default=None, ge=0)
    equity: float | None = Field(default=None, ge=0, le=1)
    call_ev_chips: Decimal | None = None
    status: Literal["partial", "complete", "unavailable"]
    assumptions: list[str] = Field(default_factory=list)


class StrategySnapshot(StrictModel):
    status: Literal["exact", "abstracted", "unavailable"]
    role: Literal["gto_solution", "reference_prior", "none"]
    confidence: float = Field(ge=0, le=1)
    source_artifact_id: str | None = None
    mismatch: dict[str, object] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)


class ExploitSnapshot(StrictModel):
    status: Literal["available", "synthetic_only", "unavailable"]
    confidence: float = Field(ge=0, le=1)
    sample_size: int = Field(default=0, ge=0)
    assumptions: list[str] = Field(default_factory=list)


class MonitorSnapshot(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    sequence: int = Field(default=0, ge=0)
    generated_at: datetime
    table_size: Literal[9]
    source_mode: Literal["synthetic_replay", "recorded_replay", "authorized_live"]
    state: HandState
    action_history: list[HandEvent]
    health: MonitorHealth
    metrics: MonitorMetrics
    replay: ReplayProgress
    poker_math: PokerMathSnapshot
    strategy: StrategySnapshot
    exploit: ExploitSnapshot
    audit: list[dict[str, object]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_snapshot_consistency(self) -> MonitorSnapshot:
        if self.table_size != self.state.table_size:
            raise ValueError("monitor table size must match the hand state")
        if self.metrics.state_revision != self.state.revision:
            raise ValueError("monitor metrics revision must match the hand state")
        if self.metrics.event_count != len(self.action_history):
            raise ValueError("monitor event count must match action history")
        if self.replay.index != len(self.action_history):
            raise ValueError("replay index must match action history length")
        return self


class MonitorEnvelope(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    sequence: int = Field(ge=1)
    kind: Literal["snapshot", "state", "event", "health"]
    emitted_at: datetime
    payload: dict[str, object]


class MonitorHistory(StrictModel):
    after_sequence: int = Field(ge=0)
    latest_sequence: int = Field(ge=0)
    gap_required: bool
    envelopes: list[MonitorEnvelope]


class ReplayStartRequest(StrictModel):
    interval_ms: int = Field(default=250, ge=25, le=5000)


class ReplaySeekRequest(StrictModel):
    index: int = Field(ge=0, le=14)
    interval_ms: int = Field(default=250, ge=25, le=5000)
