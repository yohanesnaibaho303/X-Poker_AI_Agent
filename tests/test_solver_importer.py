import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_strategy_nodes import _artifact, _key

from xpoker_agent.strategy.importer import SolverExport, load_solver_export


def _payload() -> dict[str, object]:
    return SolverExport(
        export_id="synthetic-solver-export-v1",
        generated_at=datetime(2026, 8, 26, tzinfo=UTC),
        generated_by="offline-test-solver",
        source_url="https://example.invalid/self-generated",
        source_license="Test fixture only",
        source_content_sha256="a" * 64,
        authorization="self_generated",
        artifacts=[_artifact()],
    ).model_dump(mode="json")


def test_solver_export_import_builds_hash_verified_node_library(tmp_path: Path) -> None:
    path = tmp_path / "solver-export.json"
    content = (json.dumps(_payload(), sort_keys=True) + "\n").encode()
    path.write_bytes(content)
    expected_hash = hashlib.sha256(content).hexdigest()

    imported = load_solver_export(path, expected_file_sha256=expected_hash)

    assert imported.export_file_sha256 == expected_hash
    assert imported.export.authorization == "self_generated"
    assert imported.library.lookup(_key()).distance.status == "exact"


def test_solver_export_import_rejects_changed_file_hash(tmp_path: Path) -> None:
    path = tmp_path / "solver-export.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match="file hash mismatch"):
        load_solver_export(path, expected_file_sha256="0" * 64)


def test_solver_export_requires_explicit_authorization_and_provenance() -> None:
    payload = _payload()
    payload["authorization"] = "scraped"
    payload["source_license"] = ""

    with pytest.raises(ValidationError):
        SolverExport.model_validate(payload)
