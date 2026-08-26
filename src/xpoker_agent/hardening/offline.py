"""Deterministic offline endurance, performance, and packaging evidence."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from time import perf_counter_ns
from typing import Literal

from pydantic import Field

from xpoker_agent.hardening.audit import PROJECT_ROOT, run_compatibility_audit
from xpoker_agent.models import StrictModel
from xpoker_agent.monitoring.replay import build_replay_snapshot

ArtifactKind = Literal["configuration", "template", "dependency_lock", "schema"]


class RuntimeArtifact(StrictModel):
    path: str
    kind: ArtifactKind
    content_sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=1)


class OfflineReadinessReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    passed: bool
    machine: dict[str, str]
    sessions: int = Field(ge=1)
    snapshots: int = Field(ge=15)
    replay_p95_ms: float = Field(ge=0)
    replay_budget_ms: float = Field(gt=0)
    deterministic: bool
    artifacts: list[RuntimeArtifact]
    compatibility_passed: bool
    controller_enabled: Literal[False] = False
    limitations: list[str]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(path: Path, kind: ArtifactKind) -> RuntimeArtifact:
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    return RuntimeArtifact(
        path=relative,
        kind=kind,
        content_sha256=_sha256(path),
        size_bytes=path.stat().st_size,
    )


def collect_runtime_artifacts() -> list[RuntimeArtifact]:
    required = [
        (PROJECT_ROOT / "requirements.lock", "dependency_lock"),
        (PROJECT_ROOT / "apps" / "monitor" / "package-lock.json", "dependency_lock"),
        (PROJECT_ROOT / "configs" / "game" / "initial_9max_nlh.json", "configuration"),
        (PROJECT_ROOT / "configs" / "runtime" / "default.json", "configuration"),
        (
            PROJECT_ROOT / "configs" / "layouts" / "xpoker_windows_10_portrait_9max.json",
            "configuration",
        ),
        (PROJECT_ROOT / "configs" / "ranges" / "library_manifest.json", "configuration"),
        (
            PROJECT_ROOT / "data" / "card_templates" / "xpoker_portrait_rank_templates_v1.json",
            "template",
        ),
        (
            PROJECT_ROOT
            / "data"
            / "card_templates"
            / "xpoker_portrait_hero_rank_templates_v1.json",
            "template",
        ),
    ]
    required.extend(
        (path, "schema")
        for path in sorted((PROJECT_ROOT / "schemas" / "v1").glob("*.schema.json"))
    )
    missing = [str(path) for path, _kind in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"required runtime artifacts are missing: {missing}")
    return [_artifact(path, kind) for path, kind in required]


def run_offline_readiness(
    *, sessions: int = 100, replay_budget_ms: float = 200.0
) -> OfflineReadinessReport:
    if sessions < 1:
        raise ValueError("sessions must be positive")
    latencies: list[float] = []
    signatures: set[str] = set()
    for _session in range(sessions):
        trace: list[dict[str, object]] = []
        for index in range(15):
            started = perf_counter_ns()
            snapshot = build_replay_snapshot(index)
            latencies.append((perf_counter_ns() - started) / 1_000_000)
            trace.append(
                {
                    "revision": snapshot.state.revision,
                    "street": snapshot.state.street,
                    "pot": snapshot.state.pot_main_chips,
                    "events": [event.type for event in snapshot.action_history],
                    "legal": snapshot.state.validation.legal,
                    "controller_enabled": snapshot.health.controller_enabled,
                }
            )
        signatures.add(
            hashlib.sha256(
                json.dumps(trace, sort_keys=True, default=str, separators=(",", ":")).encode()
            ).hexdigest()
        )
    ordered = sorted(latencies)
    p95 = ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)]
    compatibility = run_compatibility_audit()
    artifacts = collect_runtime_artifacts()
    deterministic = len(signatures) == 1
    passed = deterministic and p95 <= replay_budget_ms and compatibility.passed
    return OfflineReadinessReport(
        passed=passed,
        machine={
            "platform": platform.platform(),
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "architecture": platform.machine(),
        },
        sessions=sessions,
        snapshots=sessions * 15,
        replay_p95_ms=p95,
        replay_budget_ms=replay_budget_ms,
        deterministic=deterministic,
        artifacts=artifacts,
        compatibility_passed=compatibility.passed,
        controller_enabled=False,
        limitations=[
            "Synthetic replay does not satisfy live recognition or reconstruction promotion gates.",
            "No configuration-matched GTO solution is bundled.",
            "Live control remains disabled.",
        ],
    )


def write_offline_readiness(report: OfflineReadinessReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")


def machine_exit_code(report: OfflineReadinessReport) -> int:
    return 0 if report.passed else 1


if sys.version_info[:2] != (3, 12):  # pragma: no cover - package metadata also enforces this
    raise RuntimeError("offline readiness requires Python 3.12")
