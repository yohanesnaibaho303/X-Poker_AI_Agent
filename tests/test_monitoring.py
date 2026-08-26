import asyncio
from decimal import Decimal

import pytest
from fastapi import HTTPException

from xpoker_agent.api import monitor_snapshot, reference_range
from xpoker_agent.models import Position
from xpoker_agent.monitoring.hub import MonitorHub
from xpoker_agent.monitoring.replay import ReplayController, build_replay_snapshot
from xpoker_agent.simulation import run_simulated_hand


def test_simulated_monitor_replay_supports_authoritative_table() -> None:
    states, events = run_simulated_hand()
    snapshot = build_replay_snapshot(len(events))

    assert len(states) == 15
    assert snapshot.table_size == 9
    assert snapshot.state.table_status == "hand_complete"
    assert snapshot.replay.index == snapshot.replay.total == 14
    assert snapshot.health.controller_enabled is False
    assert snapshot.strategy.status == "unavailable"
    assert snapshot.poker_math.equity is None
    assert snapshot.metrics.processing_latency_ms > 0
    assert [item["status"] for item in snapshot.audit] == ["passed", "blocked", "blocked"]


def test_replay_math_exposes_exact_preflop_pot_odds_without_inventing_equity() -> None:
    snapshot = build_replay_snapshot(5)

    assert snapshot.state.next_to_act_seat == snapshot.state.hero_seat
    assert snapshot.poker_math.call_amount_chips == 2
    assert snapshot.poker_math.pot_odds_required_equity == Decimal("0.4")
    assert snapshot.poker_math.equity is None
    assert snapshot.poker_math.call_ev_chips is None


def test_replay_gto_strategy_is_always_model_abstracted() -> None:
    snapshots = [build_replay_snapshot(index) for index in range(15)]
    resolved = [snapshot for snapshot in snapshots if snapshot.strategy.hero_combo]

    assert resolved
    assert all(snapshot.strategy.role == "gto_solution" for snapshot in resolved)
    assert all(snapshot.strategy.status == "abstracted" for snapshot in resolved)
    assert all(snapshot.health.strategy_status == "abstracted" for snapshot in resolved)
    assert all(snapshot.strategy.equity is None for snapshot in resolved)
    assert all(snapshot.exploit.opponent_range_status == "unavailable" for snapshot in snapshots)

    decision = build_replay_snapshot(5)
    assert decision.strategy.hero_combo == "AsKd"
    assert decision.strategy.status == "abstracted"
    assert [item["status"] for item in decision.audit] == ["passed", "passed", "blocked"]


def test_monitor_api_exposes_fixed_table_and_reference_matrix() -> None:
    snapshot = monitor_snapshot()
    matrix = reference_range(Position.BTN)

    assert snapshot["table_size"] == 9
    assert snapshot["source_mode"] == "synthetic_replay"
    assert matrix["source"]["strategy_role"] == "reference_prior"
    assert len(matrix["cells"]) == 169


def test_reference_api_rejects_bb_rfi() -> None:
    with pytest.raises(HTTPException, match="no unopened reference prior"):
        reference_range(Position.BB)


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
        await hub.publish_snapshot(build_replay_snapshot())
        envelope = await hub.publish_snapshot(build_replay_snapshot())

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
        await controller.start(interval_ms=25)
        assert controller._task is not None  # internal task is awaited only in this regression test
        await asyncio.wait_for(controller._task, timeout=2)

        snapshot = hub.snapshot
        assert snapshot is not None
        assert snapshot.table_size == 9
        assert snapshot.replay.index == 14
        assert snapshot.replay.active is False
        assert hub.latest_sequence == 15
        assert hub.history_after(0).gap_required is False

    asyncio.run(scenario())


def test_replay_controller_can_seek_to_a_deterministic_prefix() -> None:
    async def scenario() -> None:
        hub = MonitorHub(history_limit=32)
        controller = ReplayController(hub)
        await controller.seek(index=9, interval_ms=250)

        snapshot = hub.snapshot
        assert snapshot is not None
        assert snapshot.replay.index == 9
        assert snapshot.state.street.value == "flop"
        assert len(snapshot.action_history) == 9

    asyncio.run(scenario())


def test_monitor_hub_survives_repeated_complete_session_prefixes() -> None:
    async def scenario() -> None:
        hub = MonitorHub(history_limit=64, subscriber_queue_size=4)
        queue = await hub.subscribe()
        for _session in range(20):
            for index in range(15):
                await hub.publish_snapshot(build_replay_snapshot(index))

        snapshot = hub.snapshot
        assert snapshot is not None
        assert snapshot.replay.index == 14
        assert snapshot.state.validation.legal is True
        assert hub.latest_sequence == 300
        assert hub.dropped_deliveries == 296
        assert hub.history_after(0).gap_required is True
        await hub.unsubscribe(queue)

    asyncio.run(scenario())
