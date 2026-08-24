"""Validated X-Poker visual-component catalog."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, ValidationError

from xpoker_agent.models import StrictModel
from xpoker_agent.research.registry import PROJECT_ROOT, SourceRegistry

DEFAULT_COMPONENT_CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "components.jsonl"


class ComponentRecord(StrictModel):
    component_id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    name: str
    category: Literal[
        "layout",
        "seat",
        "cards",
        "amount",
        "marker",
        "action",
        "control",
        "status",
        "history",
    ]
    critical: bool
    expected_values: list[str] = Field(default_factory=list)
    source_ids: list[UUID] = Field(default_factory=list)
    evidence_locator: str
    verification: Literal["publicly_described", "public_frame_observed", "required_unverified"]
    confidence: float = Field(ge=0, le=1)
    intended_detector: Literal["geometry", "template", "ocr", "card_classifier", "hybrid"]
    notes: str


class ComponentCatalogError(ValueError):
    """Raised when catalog records or provenance links are invalid."""


class ComponentCatalog:
    def __init__(self, records: tuple[ComponentRecord, ...], content_sha256: str) -> None:
        self.records = records
        self.content_sha256 = content_sha256

    @classmethod
    def load(
        cls,
        path: Path = DEFAULT_COMPONENT_CATALOG_PATH,
        sources: SourceRegistry | None = None,
    ) -> ComponentCatalog:
        source_registry = sources or SourceRegistry.load()
        known_source_ids = {record.source_id for record in source_registry.records}
        raw = path.read_bytes()
        records: list[ComponentRecord] = []
        for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = ComponentRecord.model_validate_json(line)
            except ValidationError as error:
                message = f"invalid component at line {line_number}: {error}"
                raise ComponentCatalogError(message) from error
            missing = set(record.source_ids) - known_source_ids
            if missing:
                raise ComponentCatalogError(
                    f"component {record.component_id} references unknown sources: {missing}"
                )
            records.append(record)

        component_ids = [record.component_id for record in records]
        if len(component_ids) != len(set(component_ids)):
            raise ComponentCatalogError("component IDs must be unique")
        return cls(tuple(records), hashlib.sha256(raw).hexdigest())

    @property
    def unresolved_critical(self) -> tuple[ComponentRecord, ...]:
        return tuple(
            record
            for record in self.records
            if record.critical and record.verification == "required_unverified"
        )
