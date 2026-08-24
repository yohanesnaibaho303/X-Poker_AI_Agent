"""Export canonical Pydantic models as versioned JSON Schemas."""

from __future__ import annotations

import json
from pathlib import Path

from xpoker_agent.capture.models import LayoutProfile
from xpoker_agent.exploit.models import (
    BestResponseAnalysis,
    ExploitAdjustment,
    NodelockResult,
    OpponentProfile,
    OpponentRangeSnapshot,
)
from xpoker_agent.models import (
    ActionAttempt,
    DecisionEnvelope,
    EvidenceRef,
    GameConfig,
    HandEvent,
    HandState,
    Observation,
    ObservationBatch,
    Provenance,
    RuntimeConfig,
    SessionSetup,
    SessionSetupRequest,
    StrategyMatch,
    WeightedRange,
)
from xpoker_agent.ranges.library import RangeArtifact
from xpoker_agent.ranges.matrix import RangeMatrix
from xpoker_agent.strategy.resolver import StrategyResolution

MODELS = [
    GameConfig,
    LayoutProfile,
    RuntimeConfig,
    SessionSetupRequest,
    SessionSetup,
    EvidenceRef,
    Provenance,
    Observation,
    ObservationBatch,
    HandEvent,
    HandState,
    WeightedRange,
    RangeArtifact,
    RangeMatrix,
    StrategyMatch,
    StrategyResolution,
    OpponentProfile,
    ExploitAdjustment,
    NodelockResult,
    OpponentRangeSnapshot,
    BestResponseAnalysis,
    DecisionEnvelope,
    ActionAttempt,
]


def main() -> None:
    output_dir = Path(__file__).resolve().parents[2] / "schemas" / "v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        output_path = output_dir / f"{model.__name__}.schema.json"
        output_path.write_text(
            json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
