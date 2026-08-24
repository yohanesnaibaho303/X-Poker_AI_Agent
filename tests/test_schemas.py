import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from xpoker_agent.models import ActionAttempt
from xpoker_agent.schema_export import MODELS


def test_all_canonical_json_schemas_are_published() -> None:
    schema_dir = Path(__file__).resolve().parents[1] / "schemas" / "v1"
    expected = {f"{model.__name__}.schema.json" for model in MODELS}
    actual = {path.name for path in schema_dir.glob("*.schema.json")}

    assert actual == expected
    for filename in expected:
        payload = json.loads((schema_dir / filename).read_text(encoding="utf-8"))
        assert payload["type"] == "object"
        assert payload["additionalProperties"] is False


def test_controller_audit_schema_rejects_executed_attempts() -> None:
    with pytest.raises(ValidationError, match="unavailable in Milestone 0"):
        ActionAttempt(
            decision_id="00000000-0000-0000-0000-000000000001",
            idempotency_token="00000000-0000-0000-0000-000000000002",
            authorization_profile_id="test-only",
            preflight_checks=[],
            target_window_fingerprint="not-configured",
            outcome="executed_verified",
        )
