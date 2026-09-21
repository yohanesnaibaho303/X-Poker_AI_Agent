"""Fail-closed audit of runtime artifacts required by the supported product scope."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import Field, model_validator

from xpoker_agent.config import load_game_config, load_runtime_config
from xpoker_agent.models import StrictModel
from xpoker_agent.ranges.library import load_seeded_gto_library, load_seeded_reference_library

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class CompatibilityCheck(StrictModel):
    check: str
    passed: bool
    detail: str
    content_sha256: str | None = Field(default=None, min_length=64, max_length=64)


class CompatibilityAudit(StrictModel):
    schema_version: str = "1.0"
    passed: bool
    checks: list[CompatibilityCheck]
    controller_enabled: bool

    @model_validator(mode="after")
    def validate_result(self) -> CompatibilityAudit:
        if self.passed != all(check.passed for check in self.checks):
            raise ValueError("audit status must equal the combined check status")
        if self.controller_enabled:
            raise ValueError("compatibility audit cannot report enabled control")
        return self


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_compatibility_audit(
    *,
    schema_dir: Path | None = None,
    dashboard_dist: Path | None = None,
) -> CompatibilityAudit:
    checks: list[CompatibilityCheck] = []

    try:
        game = load_game_config()
        game_path = PROJECT_ROOT / "configs" / "game" / "initial_9max_nlh.json"
        checks.append(
            CompatibilityCheck(
                check="authoritative_game_config",
                passed=(
                    game.seats == 9 and game.native_small_blind == 1 and game.native_big_blind == 2
                ),
                detail="9-max NLH, native SB 1 / BB 2 loaded and validated.",
                content_sha256=_hash_file(game_path),
            )
        )
    except (OSError, ValueError) as error:
        checks.append(
            CompatibilityCheck(
                check="authoritative_game_config",
                passed=False,
                detail=f"Game configuration failed validation: {error}",
            )
        )

    runtime_roots = [
        PROJECT_ROOT / "configs" / "game",
        PROJECT_ROOT / "configs" / "layouts",
        PROJECT_ROOT / "configs" / "ranges",
        PROJECT_ROOT / "data" / "ranges",
    ]
    retired_paths = sorted(
        path.relative_to(PROJECT_ROOT).as_posix()
        for root in runtime_roots
        for path in root.rglob("*")
        if path.is_file()
        and any(token in path.as_posix().casefold() for token in ("6max", "6-max"))
    )
    checks.append(
        CompatibilityCheck(
            check="retired_runtime_absent",
            passed=not retired_paths,
            detail=f"Retired six-max runtime artifacts checked; found={retired_paths}.",
        )
    )

    try:
        runtime = load_runtime_config()
        checks.append(
            CompatibilityCheck(
                check="control_lockout",
                passed=runtime.controller_enabled is False,
                detail="Runtime controller is disabled.",
            )
        )
    except (OSError, ValueError) as error:
        checks.append(
            CompatibilityCheck(
                check="control_lockout",
                passed=False,
                detail=f"Runtime configuration failed validation: {error}",
            )
        )

    try:
        library = load_seeded_reference_library()
        manifest_path = PROJECT_ROOT / "configs" / "ranges" / "library_manifest.json"
        checks.append(
            CompatibilityCheck(
                check="reference_range_library",
                passed=len(library.artifacts) == 8,
                detail="Eight non-BB 9-max reference priors passed manifest hash validation.",
                content_sha256=_hash_file(manifest_path),
            )
        )
    except (OSError, ValueError) as error:
        checks.append(
            CompatibilityCheck(
                check="reference_range_library",
                passed=False,
                detail=f"Reference range library failed validation: {error}",
            )
        )

    try:
        library = load_seeded_gto_library()
        manifest_path = PROJECT_ROOT / "configs" / "ranges" / "gtopen_manifest.json"
        checks.append(
            CompatibilityCheck(
                check="model_abstracted_gto_library",
                passed=len(library.artifacts) == 8,
                detail=(
                    "Eight owner-authorized GTOpen RFI artifacts passed hash validation; "
                    "all remain explicitly model-abstracted."
                ),
                content_sha256=_hash_file(manifest_path),
            )
        )
    except (OSError, ValueError) as error:
        checks.append(
            CompatibilityCheck(
                check="model_abstracted_gto_library",
                passed=False,
                detail=f"GTOpen range library failed validation: {error}",
            )
        )

    resolved_schema_dir = schema_dir or PROJECT_ROOT / "schemas" / "v1"
    from xpoker_agent.schema_export import MODELS  # noqa: PLC0415

    expected_schemas = {f"{model.__name__}.schema.json" for model in MODELS}
    try:
        actual_schemas = {path.name for path in resolved_schema_dir.glob("*.schema.json")}
        published = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in resolved_schema_dir.glob("*.schema.json")
        }
        missing = sorted(expected_schemas - actual_schemas)
        extra = sorted(actual_schemas - expected_schemas)
        drifted = sorted(
            name
            for model in MODELS
            if (name := f"{model.__name__}.schema.json") in published
            and published[name] != model.model_json_schema()
        )
        checks.append(
            CompatibilityCheck(
                check="published_schemas",
                passed=not missing and not extra and not drifted,
                detail=(
                    f"Schema set checked; missing={missing}, extra={extra}, drifted={drifted}."
                ),
            )
        )
    except (OSError, json.JSONDecodeError) as error:
        checks.append(
            CompatibilityCheck(
                check="published_schemas",
                passed=False,
                detail=f"Published schema validation failed: {error}",
            )
        )

    resolved_dashboard_dist = dashboard_dist or PROJECT_ROOT / "apps" / "monitor" / "dist"
    dashboard_index = resolved_dashboard_dist / "index.html"
    checks.append(
        CompatibilityCheck(
            check="dashboard_build",
            passed=dashboard_index.is_file(),
            detail=(
                "Dashboard production entry point is present."
                if dashboard_index.is_file()
                else "Dashboard production entry point is missing; run the dashboard build."
            ),
            content_sha256=_hash_file(dashboard_index) if dashboard_index.is_file() else None,
        )
    )

    return CompatibilityAudit(
        passed=all(check.passed for check in checks),
        checks=checks,
        controller_enabled=False,
    )
