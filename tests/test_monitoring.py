import asyncio

import pytest
from fastapi import HTTPException

from xpoker_agent.api import monitor_snapshot, reference_range
from xpoker_agent.models import Position
from xpoker_agent.monitoring.hub import MonitorHub
from xpoker_agent.monitoring.replay import ReplayController, build_replay_snapshot
from xpoker_agent.simulation import run_simulated_hand


@pytest.mark.parametrize("table_size", [6, 9])
def test_simulated_monitor_replay_supports_both_table_sizes(table_size: int) -> None:
    states, events = run_simulated_hand(table_size)
    snapshot = build_replay_snapshot(table_size, len(events))

    assert len(states) == 15
    assert snapshot.table_size == table_size
    assert snapshot.state.table_status == "hand_complete"
    assert snapshot.replay.index == snapshot.replay.total == 14
    assert snapshot.health.controller_enabled is False
    assert snapshot.strategy["status"] == "unavailable"


def test_monitor_api_exposes_selected_table_and_reference_matrix() -> None:
    snapshot = monitor_snapshot(6)
    matrix = reference_range(6, Position.BTN)

    assert snapshot["table_size"] == 6
    assert snapshot["source_mode"] == "synthetic_replay"
    assert matrix["source"]["strategy_role"] == "reference_prior"
    assert len(matrix["cells"]) == 169


def test_reference_api_rejects_bb_rfi() -> None:
    with pytest.raises(HTTPException, match="no unopened reference prior"):
        reference_range(9, Position.BB)


def test_monitor_hub_retains_history_and_signals_old_cursor_gap() -> None:
    async def scenario() -> None:
        hub = MonitorHub(history_limit=2)
        for index in range(3):
            await hub.publish("health", {"index": index})

        recent = hub.history_after(1)
        stale = hub.history_after(0)

        assert [item.sequence for item in recent.envelopes] == [2, 3]
        assert recent.gap_required is False
        assert stale.gap_required is True
        assert stale.envelopes == []

    asyncio.run(scenario())


def test_monitor_hub_bounds_slow_subscriber_queue_and_counts_drop() -> None:
    async def scenario() -> None:
        hub = MonitorHub(subscriber_queue_size=2)
        queue = await hub.subscribe()
        for index in range(3):
            await hub.publish("health", {"index": index})

        assert queue.qsize() == 2
        assert hub.dropped_deliveries == 1
        assert [(await queue.get()).sequence, (await queue.get()).sequence] == [2, 3]
        await hub.unsubscribe(queue)

    asyncio.run(scenario())


def test_monitor_envelope_exposes_current_sequence_and_backpressure_metrics() -> None:
    async def scenario() -> None:
        hub = MonitorHub(subscriber_queue_size=1)
        queue = await hub.subscribe()
        await hub.publish_snapshot(build_replay_snapshot(6))
        envelope = await hub.publish_snapshot(build_replay_snapshot(6))

        assert envelope.payload["sequence"] == 2
        assert envelope.payload["metrics"]["stream_sequence"] == 2
        assert envelope.payload["metrics"]["dropped_deliveries"] == 1
        assert hub.snapshot is not None
        assert hub.snapshot.metrics.dropped_deliveries == 1
        await hub.unsubscribe(queue)

    asyncio.run(scenario())


def test_replay_controller_publishes_complete_ordered_session() -> None:
    async def scenario() -> None:
        hub = MonitorHub(history_limit=32)
        controller = ReplayController(hub)
        await controller.start(table_size=6, interval_ms=25)
        assert controller._task is not None  # internal task is awaited only in this regression test
        await asyncio.wait_for(controller._task, timeout=2)

        snapshot = hub.snapshot
        assert snapshot is not None
        assert snapshot.table_size == 6
        assert snapshot.replay.index == 14
        assert snapshot.replay.active is False
        assert hub.latest_sequence == 15
        assert hub.history_after(0).gap_required is False

    asyncio.run(scenario())
