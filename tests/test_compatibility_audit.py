from pathlib import Path

from xpoker_agent.hardening import run_compatibility_audit


def test_repository_compatibility_audit_passes_with_control_disabled() -> None:
    audit = run_compatibility_audit()

    assert audit.passed is True
    assert audit.controller_enabled is False
    assert {check.check for check in audit.checks} == {
        "authoritative_game_config",
        "control_lockout",
        "dashboard_build",
        "published_schemas",
        "reference_range_library",
    }
    assert all(check.passed for check in audit.checks)


def test_audit_fails_closed_for_missing_schema_set(tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()

    audit = run_compatibility_audit(schema_dir=schema_dir)
    result = next(check for check in audit.checks if check.check == "published_schemas")

    assert audit.passed is False
    assert result.passed is False
    assert "missing=[" in result.detail


def test_audit_fails_closed_for_invalid_schema_json(tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "GameConfig.schema.json").write_text("{not-json", encoding="utf-8")

    audit = run_compatibility_audit(schema_dir=schema_dir)
    result = next(check for check in audit.checks if check.check == "published_schemas")

    assert audit.passed is False
    assert result.passed is False
    assert "failed" in result.detail.lower()


def test_audit_fails_closed_when_dashboard_build_is_missing(tmp_path: Path) -> None:
    audit = run_compatibility_audit(dashboard_dist=tmp_path / "missing-dashboard")
    result = next(check for check in audit.checks if check.check == "dashboard_build")

    assert audit.passed is False
    assert result.passed is False
    assert "missing" in result.detail.lower()
