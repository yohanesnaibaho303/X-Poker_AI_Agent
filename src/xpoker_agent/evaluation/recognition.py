"""Versioned recognition metrics that cannot promote synthetic/calibration evidence."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from xpoker_agent.evaluation.metrics import percentile_95
from xpoker_agent.models import StrictModel


class RecognitionEvaluationCase(StrictModel):
    case_id: str
    component: Literal["card", "numeric_ocr", "street", "seat", "action_control"]
    dataset_slice: str
    expected: str | None
    predicted: str | None
    accepted: bool
    confidence: float = Field(ge=0, le=1)
    latency_ms: float = Field(ge=0)
    evidence_sha256: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_acceptance(self) -> RecognitionEvaluationCase:
        if self.accepted != (self.predicted is not None):
            raise ValueError("accepted recognition must have exactly one predicted value")
        return self


class RecognitionSliceMetrics(StrictModel):
    dataset_slice: str
    total: int = Field(ge=1)
    correct: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    exact_accuracy: float = Field(ge=0, le=1)
    safe_rejection_rate: float | None = Field(default=None, ge=0, le=1)
    mean_confidence: float = Field(ge=0, le=1)
    p95_latency_ms: float = Field(ge=0)


class RecognitionEvaluationReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    component: Literal["card", "numeric_ocr", "street", "seat", "action_control"]
    component_version: str
    dataset_id: str
    dataset_role: Literal["calibration", "regression", "holdout"]
    dataset_sha256: str = Field(min_length=64, max_length=64)
    target_accuracy: float = Field(ge=0, le=1)
    overall: RecognitionSliceMetrics
    slices: list[RecognitionSliceMetrics]
    promotion_eligible: bool
    gate_passed: bool
    limitations: list[str]

    @model_validator(mode="after")
    def prevent_non_holdout_promotion(self) -> RecognitionEvaluationReport:
        if self.promotion_eligible != (self.dataset_role == "holdout"):
            raise ValueError("only holdout datasets can be promotion eligible")
        expected_gate = (
            self.promotion_eligible and self.overall.exact_accuracy >= self.target_accuracy
        )
        if self.gate_passed != expected_gate:
            raise ValueError("gate status must use holdout eligibility and target accuracy")
        return self


def _metrics(dataset_slice: str, cases: list[RecognitionEvaluationCase]) -> RecognitionSliceMetrics:
    correct = sum(case.accepted and case.predicted == case.expected for case in cases)
    false_positives = sum(
        case.accepted and case.predicted != case.expected for case in cases
    )
    false_negatives = sum(
        case.expected is not None and not (case.accepted and case.predicted == case.expected)
        for case in cases
    )
    unsupported = [case for case in cases if case.expected is None]
    safe_rejections = sum(not case.accepted for case in unsupported)
    return RecognitionSliceMetrics(
        dataset_slice=dataset_slice,
        total=len(cases),
        correct=correct,
        false_positives=false_positives,
        false_negatives=false_negatives,
        exact_accuracy=correct / len(cases),
        safe_rejection_rate=(safe_rejections / len(unsupported) if unsupported else None),
        mean_confidence=sum(case.confidence for case in cases) / len(cases),
        p95_latency_ms=percentile_95([case.latency_ms for case in cases]),
    )


def evaluate_recognition_cases(
    cases: list[RecognitionEvaluationCase],
    *,
    component_version: str,
    dataset_id: str,
    dataset_role: Literal["calibration", "regression", "holdout"],
    target_accuracy: float,
) -> RecognitionEvaluationReport:
    if not cases:
        raise ValueError("recognition evaluation requires at least one case")
    components = {case.component for case in cases}
    if len(components) != 1:
        raise ValueError("one recognition report cannot mix components")
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("recognition case IDs must be unique")
    normalized = [
        case.model_dump(mode="json")
        for case in sorted(cases, key=lambda item: item.case_id)
    ]
    dataset_sha256 = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    grouped: dict[str, list[RecognitionEvaluationCase]] = defaultdict(list)
    for case in cases:
        grouped[case.dataset_slice].append(case)
    overall = _metrics("all", cases)
    promotion_eligible = dataset_role == "holdout"
    return RecognitionEvaluationReport(
        component=components.pop(),
        component_version=component_version,
        dataset_id=dataset_id,
        dataset_role=dataset_role,
        dataset_sha256=dataset_sha256,
        target_accuracy=target_accuracy,
        overall=overall,
        slices=[_metrics(name, grouped[name]) for name in sorted(grouped)],
        promotion_eligible=promotion_eligible,
        gate_passed=promotion_eligible and overall.exact_accuracy >= target_accuracy,
        limitations=(
            []
            if promotion_eligible
            else ["Calibration and regression data cannot satisfy a promotion gate."]
        ),
    )


def load_recognition_cases(path: Path) -> list[RecognitionEvaluationCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("recognition dataset must be a JSON array")
    return [RecognitionEvaluationCase.model_validate(item) for item in payload]


def write_recognition_report(report: RecognitionEvaluationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
