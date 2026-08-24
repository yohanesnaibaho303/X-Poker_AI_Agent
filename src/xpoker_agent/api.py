"""Local inspectable API boundary for development and monitoring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from xpoker_agent import __version__
from xpoker_agent.config import load_game_config, load_runtime_config
from xpoker_agent.logging import configure_logging
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


@app.get("/v1/controller/status")
def controller_status() -> dict[str, object]:
    return {
        "enabled": False,
        "available": False,
        "reason": "Control is unavailable until the required acceptance gates pass.",
    }
