"""Local inspectable API boundary for development and monitoring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI

from xpoker_agent import __version__
from xpoker_agent.capture.profile import load_target_profile, match_authorized_target
from xpoker_agent.capture.windows import discover_xpoker_windows
from xpoker_agent.config import load_game_config, load_runtime_config
from xpoker_agent.logging import configure_logging
from xpoker_agent.research.assets import AssetManifest
from xpoker_agent.research.catalog import ComponentCatalog
from xpoker_agent.research.registry import SourceRegistry
from xpoker_agent.simulation import run_simulated_hand


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    load_game_config()
    load_runtime_config()
    yield


app = FastAPI(
    title="X-Poker AI Agent",
    version=__version__,
    description="Local observation-first API. Table control is disabled.",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, object]:
    runtime = load_runtime_config()
    return {
        "status": "ok",
        "version": __version__,
        "mode": runtime.mode,
        "controller_enabled": runtime.controller_enabled,
    }


@app.get("/v1/config/game")
def game_config(table_size: Literal[6, 9] = 9) -> dict[str, object]:
    return load_game_config(table_size=table_size).model_dump(mode="json")


@app.get("/v1/config/games")
def supported_game_configs() -> dict[str, object]:
    configurations = [load_game_config(table_size=size) for size in (6, 9)]
    return {
        "supported_table_sizes": [6, 9],
        "configurations": [config.model_dump(mode="json") for config in configurations],
    }


@app.get("/v1/simulation/hand")
def simulation_hand() -> dict[str, object]:
    states, events = run_simulated_hand()
    return {
        "events": [event.model_dump(mode="json") for event in events],
        "states": [state.model_dump(mode="json") for state in states],
    }


@app.get("/v1/research/sources")
def research_sources() -> dict[str, object]:
    registry = SourceRegistry.load()
    return {
        "content_sha256": registry.content_sha256,
        "count": len(registry.records),
        "sources": [record.model_dump(mode="json") for record in registry.records],
    }


@app.get("/v1/research/components")
def research_components() -> dict[str, object]:
    catalog = ComponentCatalog.load()
    return {
        "content_sha256": catalog.content_sha256,
        "count": len(catalog.records),
        "unresolved_critical": len(catalog.unresolved_critical),
        "components": [record.model_dump(mode="json") for record in catalog.records],
    }


@app.get("/v1/research/assets")
def research_assets() -> dict[str, object]:
    manifest = AssetManifest.load()
    return {
        "content_sha256": manifest.content_sha256,
        "count": len(manifest.records),
        "pending_review": len(manifest.pending_review),
        "assets": [record.model_dump(mode="json") for record in manifest.records],
    }


@app.get("/v1/controller/status")
def controller_status() -> dict[str, object]:
    return {
        "enabled": False,
        "available": False,
        "reason": "Control is unavailable until the required acceptance gates pass.",
    }


@app.get("/v1/capture/status")
def capture_status() -> dict[str, object]:
    profile = load_target_profile()
    candidates = discover_xpoker_windows(classify_visual_role=True)
    matches = [match_authorized_target(candidate, profile) for candidate in candidates]
    return {
        "runtime_target": "X-Poker",
        "profile_id": profile.profile_id,
        "authorization_enabled": profile.enabled,
        "candidate_count": len(candidates),
        "eligible_count": sum(match.eligible for match in matches),
        "capture_active": False,
    }
