"""Export canonical Pydantic models as versioned JSON Schemas."""

from __future__ import annotations

import json
from pathlib import Path

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
    StrategyMatch,
    WeightedRange,
)

MODELS = [
    GameConfig,
    RuntimeConfig,
    EvidenceRef,
    Provenance,
    Observation,
    ObservationBatch,
    HandEvent,
    HandState,
    WeightedRange,
    StrategyMatch,
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
