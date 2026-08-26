from pathlib import Path

import pytest

from xpoker_agent.hardening.offline import collect_runtime_artifacts, run_offline_readiness


def test_runtime_manifest_contains_locks_templates_config_and_schemas() -> None:
    artifacts = collect_runtime_artifacts()

    assert {item.kind for item in artifacts} == {
        "configuration",
        "template",
        "dependency_lock",
        "schema",
    }
    assert len({item.path for item in artifacts}) == len(artifacts)
    assert all("6max" not in item.path.lower() for item in artifacts)
    assert all(len(item.content_sha256) == 64 for item in artifacts)


def test_offline_readiness_is_deterministic_and_control_locked() -> None:
    report = run_offline_readiness(sessions=2, replay_budget_ms=1_000)

    assert report.passed is True
    assert report.snapshots == 30
    assert report.deterministic is True
    assert report.compatibility_passed is True
    assert report.controller_enabled is False


def test_offline_readiness_fails_closed_on_performance_budget() -> None:
    report = run_offline_readiness(sessions=1, replay_budget_ms=0.000001)

    assert report.passed is False


def test_offline_readiness_rejects_zero_sessions() -> None:
    with pytest.raises(ValueError, match="positive"):
        run_offline_readiness(sessions=0)


def test_runtime_artifact_paths_are_relative() -> None:
    assert all(not Path(item.path).is_absolute() for item in collect_runtime_artifacts())
