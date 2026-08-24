"""Local inspectable API boundary for development and monitoring."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from xpoker_agent import __version__
from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.capture.profile import load_target_profile, match_authorized_target
from xpoker_agent.capture.windows import discover_xpoker_windows
from xpoker_agent.chips import create_session_setup
from xpoker_agent.config import load_game_config, load_runtime_config
from xpoker_agent.logging import configure_logging
from xpoker_agent.models import Position, SessionSetupRequest, positions_for_table_size
from xpoker_agent.monitoring import MonitorHub, ReplayController, build_replay_snapshot
from xpoker_agent.monitoring.models import ReplaySeekRequest, ReplayStartRequest
from xpoker_agent.ranges.library import (
    ObservedRangeAction,
    PreflopSpotKey,
    load_seeded_reference_library,
)
from xpoker_agent.ranges.matrix import project_range_matrix
from xpoker_agent.research.assets import AssetManifest
from xpoker_agent.research.catalog import ComponentCatalog
from xpoker_agent.research.registry import SourceRegistry
from xpoker_agent.simulation import run_simulated_hand
from xpoker_agent.vision.live import diagnose_authorized_table

monitor_hub = MonitorHub()
replay_controller = ReplayController(monitor_hub)
latest_live_frame: CapturedFrame | None = None
live_capture_lock = asyncio.Lock()


def require_table_size(value: int) -> Literal[6, 9]:
    if value not in (6, 9):
        raise HTTPException(status_code=422, detail="table_size must be 6 or 9")
    return cast(Literal[6, 9], value)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    load_game_config()
    load_runtime_config()
    yield
    await replay_controller.stop()


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
def game_config(table_size: int = 9) -> dict[str, object]:
    return load_game_config(table_size=require_table_size(table_size)).model_dump(mode="json")


@app.get("/v1/config/games")
def supported_game_configs() -> dict[str, object]:
    configurations = [load_game_config(table_size=size) for size in (6, 9)]
    return {
        "supported_table_sizes": [6, 9],
        "configurations": [config.model_dump(mode="json") for config in configurations],
    }


@app.post("/v1/session/setup/preview")
def preview_session_setup(request: SessionSetupRequest) -> dict[str, object]:
    setup = create_session_setup(
        table_size=request.table_size,
        chip_display_mode=request.chip_display_mode,
        stack_input=request.stack_input,
        big_blind_native_chips=request.big_blind_native_chips,
    )
    return setup.model_dump(mode="json")


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


@app.post("/v1/capture/diagnostic")
async def capture_diagnostic() -> dict[str, object]:
    global latest_live_frame
    async with live_capture_lock:
        try:
            diagnostic, frame = await diagnose_authorized_table()
        except (OSError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        latest_live_frame = frame
    return diagnostic.model_dump(mode="json")


@app.get("/v1/capture/latest.bmp", response_class=Response)
def latest_capture_frame() -> Response:
    if latest_live_frame is None:
        raise HTTPException(status_code=404, detail="no authorized capture diagnostic exists")
    return Response(
        content=latest_live_frame.to_bmp(),
        media_type="image/bmp",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/v1/ranges/reference")
def reference_range(table_size: int, position: Position) -> dict[str, object]:
    table_size = require_table_size(table_size)
    positions = positions_for_table_size(table_size)
    if position is Position.BB or position not in positions:
        raise HTTPException(status_code=404, detail="no unopened reference prior for this position")
    position_index = positions.index(position)
    prior_positions = [item for item in positions[:position_index] if item is not Position.BB]
    spot = PreflopSpotKey(
        seats=table_size,
        stack_depth_bb=100,
        player_position=position,
        players_remaining=table_size - position_index,
        action_sequence=[
            ObservedRangeAction(actor_position=item, type="fold") for item in prior_positions
        ],
    )
    artifact = load_seeded_reference_library(table_size).lookup(spot).artifact
    weighted = artifact.to_weighted_range(
        player_ref="monitor-reference",
        hand_id=UUID("80000000-0000-0000-0000-000000000001"),
    )
    return project_range_matrix(weighted).model_dump(mode="json")


@app.get("/v1/monitor/snapshot")
def monitor_snapshot(table_size: int = 9) -> dict[str, object]:
    table_size = require_table_size(table_size)
    snapshot = monitor_hub.snapshot
    if snapshot is None or snapshot.table_size != table_size:
        snapshot = build_replay_snapshot(table_size)
    return snapshot.model_dump(mode="json")


@app.get("/v1/monitor/events")
def monitor_events(after_sequence: int = 0) -> dict[str, object]:
    try:
        history = monitor_hub.history_after(after_sequence)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return history.model_dump(mode="json")


@app.post("/v1/monitor/replay/start")
async def start_monitor_replay(request: ReplayStartRequest) -> dict[str, object]:
    await replay_controller.start(
        table_size=request.table_size,
        interval_ms=request.interval_ms,
    )
    return {
        "started": True,
        "table_size": request.table_size,
        "interval_ms": request.interval_ms,
        "controller_enabled": False,
    }


@app.post("/v1/monitor/replay/stop")
async def stop_monitor_replay() -> dict[str, object]:
    await replay_controller.stop()
    return {"stopped": True, "controller_enabled": False}


@app.post("/v1/monitor/replay/seek")
async def seek_monitor_replay(request: ReplaySeekRequest) -> dict[str, object]:
    await replay_controller.seek(
        table_size=request.table_size,
        index=request.index,
        interval_ms=request.interval_ms,
    )
    return {
        "seeked": True,
        "table_size": request.table_size,
        "index": request.index,
        "controller_enabled": False,
    }


@app.websocket("/v1/monitor/stream")
async def monitor_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = await monitor_hub.subscribe()
    try:
        snapshot = monitor_hub.snapshot or build_replay_snapshot(9)
        await websocket.send_json(
            {
                "schema_version": "1.0",
                "sequence": monitor_hub.latest_sequence,
                "kind": "snapshot",
                "payload": snapshot.model_dump(mode="json"),
            }
        )
        while True:
            try:
                envelope = await asyncio.wait_for(queue.get(), timeout=5.0)
                await websocket.send_json(envelope.model_dump(mode="json"))
            except TimeoutError:
                await websocket.send_json(
                    {
                        "schema_version": "1.0",
                        "sequence": monitor_hub.latest_sequence,
                        "kind": "heartbeat",
                        "payload": {"controller_enabled": False},
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        await monitor_hub.unsubscribe(queue)


MONITOR_DIST = Path(__file__).resolve().parents[2] / "apps" / "monitor" / "dist"
if MONITOR_DIST.exists():
    app.mount("/monitor", StaticFiles(directory=MONITOR_DIST, html=True), name="monitor")
