"""Fail-closed reconstruction evaluation over frozen replay outcomes."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from xpoker_agent.evaluation.metrics import percentile_95
from xpoker_agent.models import StrictModel


class ReconstructionEvaluationCase(StrictModel):
    case_id: str
    replay_sha256: str = Field(min_length=64, max_length=64)
    dataset_slice: str
    supported: bool
    exact_match: bool
    safely_stopped: bool
    latency_ms: float = Field(ge=0)
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> ReconstructionEvaluationCase:
        if self.exact_match and self.safely_stopped:
            raise ValueError("a replay cannot both match and stop")
        if not self.supported and self.exact_match:
            raise ValueError("unsupported replay cannot be an exact supported reconstruction")
        if self.failure_reason is not None and (self.exact_match or self.safely_stopped is False):
            raise ValueError("failure reason belongs only to safely stopped outcomes")
        return self


class ReconstructionMetrics(StrictModel):
    total: int = Field(ge=1)
    supported_total: int = Field(ge=0)
    exact_supported: int = Field(ge=0)
    unsupported_total: int = Field(ge=0)
    safely_stopped_unsupported: int = Field(ge=0)
    exact_accuracy: float | None = Field(default=None, ge=0, le=1)
    unsupported_safe_rate: float | None = Field(default=None, ge=0, le=1)
    p95_latency_ms: float = Field(ge=0)


class ReconstructionEvaluationReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    reducer_version: str
    dataset_id: str
    dataset_role: Literal["regression", "holdout"]
    dataset_sha256: str = Field(min_length=64, max_length=64)
    target_accuracy: float = Field(default=0.98, ge=0, le=1)
    metrics: ReconstructionMetrics
    promotion_eligible: bool
    gate_passed: bool
    limitations: list[str]

    @model_validator(mode="after")
    def validate_gate(self) -> ReconstructionEvaluationReport:
        if self.promotion_eligible != (self.dataset_role == "holdout"):
            raise ValueError("only holdout reconstruction data can be promotion eligible")
        exact_passed = (
            self.metrics.exact_accuracy is not None
            and self.metrics.exact_accuracy >= self.target_accuracy
        )
        safe_passed = (
            self.metrics.unsupported_safe_rate is None
            or self.metrics.unsupported_safe_rate == 1.0
        )
        if self.gate_passed != (self.promotion_eligible and exact_passed and safe_passed):
            raise ValueError("gate status must include holdout, accuracy, and safe rejection")
        return self


def evaluate_reconstruction_cases(
    cases: list[ReconstructionEvaluationCase],
    *,
    reducer_version: str,
    dataset_id: str,
    dataset_role: Literal["regression", "holdout"],
    target_accuracy: float = 0.98,
) -> ReconstructionEvaluationReport:
    if not cases:
        raise ValueError("reconstruction evaluation requires cases")
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("reconstruction case IDs must be unique")
    normalized = [
        case.model_dump(mode="json") for case in sorted(cases, key=lambda item: item.case_id)
    ]
    dataset_sha256 = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    supported = [case for case in cases if case.supported]
    unsupported = [case for case in cases if not case.supported]
    exact_accuracy = (
        sum(case.exact_match for case in supported) / len(supported) if supported else None
    )
    safe_rate = (
        sum(case.safely_stopped for case in unsupported) / len(unsupported)
        if unsupported
        else None
    )
    metrics = ReconstructionMetrics(
        total=len(cases),
        supported_total=len(supported),
        exact_supported=sum(case.exact_match for case in supported),
        unsupported_total=len(unsupported),
        safely_stopped_unsupported=sum(case.safely_stopped for case in unsupported),
        exact_accuracy=exact_accuracy,
        unsupported_safe_rate=safe_rate,
        p95_latency_ms=percentile_95([case.latency_ms for case in cases]),
    )
    promotion_eligible = dataset_role == "holdout"
    gate_passed = (
        promotion_eligible
        and exact_accuracy is not None
        and exact_accuracy >= target_accuracy
        and (safe_rate is None or safe_rate == 1.0)
    )
    return ReconstructionEvaluationReport(
        reducer_version=reducer_version,
        dataset_id=dataset_id,
        dataset_role=dataset_role,
        dataset_sha256=dataset_sha256,
        target_accuracy=target_accuracy,
        metrics=metrics,
        promotion_eligible=promotion_eligible,
        gate_passed=gate_passed,
        limitations=(
            []
            if promotion_eligible
            else ["Regression fixtures cannot satisfy the reconstruction promotion gate."]
        ),
    )
