"""Validated import boundary for licensed, generated, or authorized solver exports."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from xpoker_agent.models import StrictModel
from xpoker_agent.strategy.nodes import StrategyNodeArtifact, StrategyNodeLibrary


class SolverExport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    export_id: str
    generated_at: datetime
    generated_by: str
    source_url: str
    source_license: str
    source_content_sha256: str = Field(min_length=64, max_length=64)
    authorization: Literal["licensed", "self_generated", "user_authorized"]
    artifacts: list[StrategyNodeArtifact]

    @model_validator(mode="after")
    def validate_export(self) -> SolverExport:
        if not self.source_url or not self.source_license:
            raise ValueError("solver export requires source URL and license")
        if not self.artifacts:
            raise ValueError("solver export cannot be empty")
        artifact_ids = [artifact.artifact_id for artifact in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("solver export contains duplicate artifact IDs")
        return self


@dataclass(frozen=True)
class ImportedSolverExport:
    export: SolverExport
    export_file_sha256: str
    library: StrategyNodeLibrary


def load_solver_export(
    path: Path, *, expected_file_sha256: str | None = None
) -> ImportedSolverExport:
    content = path.read_bytes()
    file_sha256 = hashlib.sha256(content).hexdigest()
    if expected_file_sha256 is not None and file_sha256 != expected_file_sha256:
        raise ValueError(
            f"solver export file hash mismatch: expected {expected_file_sha256}, got {file_sha256}"
        )
    export = SolverExport.model_validate_json(content)
    library = StrategyNodeLibrary(export.artifacts)
    return ImportedSolverExport(
        export=export,
        export_file_sha256=file_sha256,
        library=library,
    )
