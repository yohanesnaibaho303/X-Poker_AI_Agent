"""Replay-backed monitoring snapshots for deterministic UI integration."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter_ns

from xpoker_agent.models import HandState, ParticipationStatus
from xpoker_agent.monitoring.hub import MonitorHub
from xpoker_agent.monitoring.models import (
    ExploitSnapshot,
    MonitorHealth,
    MonitorMetrics,
    MonitorSnapshot,
    PokerMathSnapshot,
    ReplayProgress,
    StrategySnapshot,
)
from xpoker_agent.poker_math import effective_stack, pot_odds_required_equity, stack_to_pot_ratio
from xpoker_agent.simulation import run_simulated_hand


def _replay_math(state: HandState) -> PokerMathSnapshot:
    hero = state.seats[state.hero_seat]
    opponents = [
        seat
        for seat in state.seats
        if seat.seat != state.hero_seat
        and seat.participation in {ParticipationStatus.ACTIVE, ParticipationStatus.ALL_IN}
    ]
    effective_stack_chips: Decimal | None = None
    if opponents:
        effective_stack_chips = effective_stack(
            hero.stack_chips, *(seat.stack_chips for seat in opponents)
        )

    call_chips = Decimal("0")
    required_equity: Decimal | None = None
    if state.next_to_act_seat == state.hero_seat and state.street.value != "none":
        hero_committed = hero.committed_by_street_chips.get(state.street, Decimal("0"))
        call_chips = max(Decimal("0"), state.current_bet_chips - hero_committed)
        if call_chips > 0:
            required_equity = pot_odds_required_equity(state.pot_main_chips, call_chips)

    spr: Decimal | None = None
    if effective_stack_chips is not None and state.pot_main_chips > 0:
        spr = stack_to_pot_ratio(effective_stack_chips, state.pot_main_chips)

    return PokerMathSnapshot(
        effective_stack_chips=effective_stack_chips,
        call_amount_chips=call_chips,
        pot_odds_required_equity=required_equity,
        spr=spr,
        equity=None,
        call_ev_chips=None,
        status="partial",
        assumptions=[
            "Pot odds and SPR are deterministic from the reconstructed state.",
            "Equity and call EV remain unavailable without a validated opponent range.",
        ],
    )


def build_replay_snapshot(
    index: int = 0,
    *,
    active: bool = False,
    interval_ms: int = 250,
) -> MonitorSnapshot:
    started_ns = perf_counter_ns()
    states, events = run_simulated_hand()
    if index < 0 or index > len(events):
        raise ValueError("replay index is outside the simulated hand")
    state = states[index]
    history = events[:index]
    warnings = [
        "Synthetic replay only; no authorized live table is connected.",
        "Configuration-matched GTO strategy is unavailable.",
        "Table control is disabled.",
    ]
    snapshot = MonitorSnapshot(
        generated_at=datetime.now(UTC),
        table_size=9,
        source_mode="synthetic_replay",
        state=state,
        action_history=history,
        health=MonitorHealth(status="degraded", warnings=warnings),
        metrics=MonitorMetrics(
            state_revision=state.revision,
            event_count=len(history),
            processing_latency_ms=0,
        ),
        replay=ReplayProgress(
            active=active,
            index=index,
            total=len(events),
            interval_ms=interval_ms,
        ),
        poker_math=_replay_math(state),
        strategy=StrategySnapshot(
            status="unavailable",
            role="reference_prior",
            confidence=0.55,
            assumptions=["Reference prior may be displayed separately but is not exact GTO."],
        ),
        exploit=ExploitSnapshot(
            status="synthetic_only",
            confidence=0.0,
            sample_size=0,
            assumptions=["No live opponent sample is connected."],
        ),
        audit=[
            {
                "check": "state_legality",
                "status": "passed" if state.validation.legal else "failed",
                "detail": "The deterministic reducer accepted every replay transition.",
                "source": "xpoker_agent.state.HandStateReducer",
            },
            {
                "check": "strategy_source",
                "status": "blocked",
                "detail": "No configuration-matched GTO artifact is installed.",
                "source": "strategy resolver",
            },
            {
                "check": "table_control",
                "status": "blocked",
                "detail": "Controller implementation and arming are absent.",
                "source": "runtime safety boundary",
            },
        ],
    )
    latency_ms = (perf_counter_ns() - started_ns) / 1_000_000
    return snapshot.model_copy(
        update={
            "metrics": snapshot.metrics.model_copy(update={"processing_latency_ms": latency_ms})
        }
    )


class ReplayController:
    def __init__(self, hub: MonitorHub) -> None:
        self.hub = hub
        self._task: asyncio.Task[None] | None = None

    @property
    def active(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, *, interval_ms: int) -> None:
        await self.stop()
        self._task = asyncio.create_task(self._run(interval_ms))

    async def seek(self, *, index: int, interval_ms: int) -> None:
        await self.stop()
        await self.hub.publish_snapshot(
            build_replay_snapshot(index, active=False, interval_ms=interval_ms)
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        if not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    async def _run(self, interval_ms: int) -> None:
        _, events = run_simulated_hand()
        await self.hub.publish_snapshot(
            build_replay_snapshot(0, active=True, interval_ms=interval_ms)
        )
        for index, event in enumerate(events, start=1):
            await asyncio.sleep(interval_ms / 1000)
            snapshot = build_replay_snapshot(
                index,
                active=index < len(events),
                interval_ms=interval_ms,
            )
            await self.hub.publish(
                "event",
                {
                    "event": event.model_dump(mode="json"),
                    "snapshot": snapshot.model_dump(mode="json"),
                },
                snapshot=snapshot,
            )
