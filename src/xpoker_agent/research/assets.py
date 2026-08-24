"""Research asset manifests without indiscriminate copyrighted-asset retention."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, ValidationError, model_validator

from xpoker_agent.models import StrictModel
from xpoker_agent.research.registry import PROJECT_ROOT, SourceRegistry

DEFAULT_ASSET_MANIFEST_PATH = PROJECT_ROOT / "data" / "catalog" / "assets.jsonl"


class AssetClassification(StrictModel):
    xpoker_version: str = "unknown"
    layout: str = "unknown"
    theme: str = "unknown"
    orientation: Literal["portrait", "landscape", "mixed", "unknown"] = "unknown"
    game_type: str = "unknown"
    street: Literal["none", "preflop", "flop", "turn", "river", "showdown", "mixed", "unknown"]
    components: list[str] = Field(default_factory=list)


class AssetRecord(StrictModel):
    asset_id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    source_id: UUID
    kind: Literal["screenshot_set", "video", "transcript", "frame", "article_summary"]
    locator: str
    retention: Literal["metadata_only", "permitted_local", "quarantined"]
    license_review: Literal["pending", "reference_only", "approved"]
    local_path: str | None = None
    content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    classification: AssetClassification
    confidence: float = Field(ge=0, le=1)
    notes: str

    @model_validator(mode="after")
    def validate_retention(self) -> AssetRecord:
        if self.retention == "permitted_local" and (
            self.local_path is None or self.content_sha256 is None
        ):
            raise ValueError("permitted local assets require a path and content hash")
        if self.retention != "permitted_local" and self.local_path is not None:
            raise ValueError("metadata-only or quarantined assets cannot expose a local path")
        return self


class AssetManifestError(ValueError):
    """Raised when research asset metadata is invalid."""


class AssetManifest:
    def __init__(self, records: tuple[AssetRecord, ...], content_sha256: str) -> None:
        self.records = records
        self.content_sha256 = content_sha256

    @classmethod
    def load(
        cls,
        path: Path = DEFAULT_ASSET_MANIFEST_PATH,
        sources: SourceRegistry | None = None,
    ) -> AssetManifest:
        source_registry = sources or SourceRegistry.load()
        known_sources = {record.source_id for record in source_registry.records}
        raw = path.read_bytes()
        records: list[AssetRecord] = []
        for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = AssetRecord.model_validate_json(line)
            except ValidationError as error:
                message = f"invalid asset at line {line_number}: {error}"
                raise AssetManifestError(message) from error
            if record.source_id not in known_sources:
                raise AssetManifestError(f"asset {record.asset_id} references an unknown source")
            records.append(record)
        asset_ids = [record.asset_id for record in records]
        if len(asset_ids) != len(set(asset_ids)):
            raise AssetManifestError("asset IDs must be unique")
        return cls(tuple(records), hashlib.sha256(raw).hexdigest())

    @property
    def pending_review(self) -> tuple[AssetRecord, ...]:
        return tuple(record for record in self.records if record.license_review == "pending")
