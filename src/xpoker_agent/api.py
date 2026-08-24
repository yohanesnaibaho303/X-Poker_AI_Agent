"""Local inspectable API boundary for development and monitoring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from xpoker_agent import __version__
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
def game_config() -> dict[str, object]:
    return load_game_config().model_dump(mode="json")


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
