"""Validated source-registry loading for provenance-first research."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from xpoker_agent.models import Provenance

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "data" / "catalog" / "sources.jsonl"


class SourceRegistryError(ValueError):
    """Raised when the source registry is malformed or internally inconsistent."""


class SourceRegistry:
    def __init__(self, records: tuple[Provenance, ...], content_sha256: str) -> None:
        self.records = records
        self.content_sha256 = content_sha256

    @classmethod
    def load(cls, path: Path = DEFAULT_REGISTRY_PATH) -> SourceRegistry:
        raw = path.read_bytes()
        records: list[Provenance] = []
        for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                record = Provenance.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as error:
                message = f"invalid source at line {line_number}: {error}"
                raise SourceRegistryError(message) from error
            parsed = urlparse(record.url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise SourceRegistryError(f"source line {line_number} has an invalid web URL")
            records.append(record)

        source_ids = [record.source_id for record in records]
        urls = [record.url.rstrip("/") for record in records]
        if len(source_ids) != len(set(source_ids)):
            raise SourceRegistryError("source IDs must be unique")
        if len(urls) != len(set(urls)):
            raise SourceRegistryError("normalized source URLs must be unique")
        return cls(tuple(records), hashlib.sha256(raw).hexdigest())

    def by_type(self, source_type: str) -> tuple[Provenance, ...]:
        return tuple(record for record in self.records if record.source_type == source_type)

    def by_fact_class(self, fact_class: str) -> tuple[Provenance, ...]:
        return tuple(record for record in self.records if record.fact_class == fact_class)
