"""Replay-backed monitoring snapshots for deterministic UI integration."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from time import perf_counter_ns

from xpoker_agent.models import HandState, ParticipationStatus, Position, Street
from xpoker_agent.monitoring.hub import MonitorHub
from xpoker_agent.monitoring.models import (
    ExploitSnapshot,
    MonitorHealth,
    MonitorMetrics,
    MonitorSnapshot,
    PokerMathSnapshot,
    ReplayProgress,
    StrategyActionSnapshot,
    StrategySnapshot,
)
from xpoker_agent.poker_math import effective_stack, pot_odds_required_equity, stack_to_pot_ratio
from xpoker_agent.ranges.cards import canonical_combo
from xpoker_agent.ranges.library import (
    ObservedRangeAction,
    PreflopSpotKey,
    load_seeded_gto_library,
    load_seeded_reference_library,
)
from xpoker_agent.simulation import run_simulated_hand
from xpoker_agent.strategy.resolver import PreflopStrategyResolver


@lru_cache(maxsize=1)
def _strategy_resolver() -> PreflopStrategyResolver:
    return PreflopStrategyResolver(
        gto_library=load_seeded_gto_library(),
        reference_library=load_seeded_reference_library(),
    )


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


def _replay_strategy(state: HandState) -> StrategySnapshot:
    if (
        state.hero_position is not Position.BTN
        or len(state.hero_cards) != 2
        or state.street is not Street.PREFLOP
        or state.next_to_act_seat != state.hero_seat
    ):
        return StrategySnapshot(
            status="unavailable",
            role="reference_prior",
            confidence=0.0,
            assumptions=[
                "Reference strategy waits for stable hero cards and a supported unopened position."
            ],
        )
    positions = [
        Position.UTG,
        Position.UTG_1,
        Position.UTG_2,
        Position.LJ,
        Position.HJ,
        Position.CO,
    ]
    spot = PreflopSpotKey(
        stack_depth_chips=state.seats[state.hero_seat].starting_stack_chips,
        player_position=Position.BTN,
        players_remaining=3,
        action_sequence=[
            ObservedRangeAction(actor_position=position, type="fold")
            for position in positions
        ],
    )
    combo = canonical_combo(*state.hero_cards)
    resolution = _strategy_resolver().resolve(
        spot, player_ref="hero", hand_id=state.hand_id
    )
    try:
        result = _strategy_resolver().summarize_combo(resolution, combo)
    except KeyError:
        return StrategySnapshot(
            status="unavailable",
            role="none",
            confidence=0.0,
            hero_combo=combo,
            assumptions=["Hero combination is absent from available strategy artifacts."],
        )
    return StrategySnapshot(
        status=result.match_status,
        role=result.strategy_role,
        confidence=result.confidence,
        source_artifact_id=result.source_artifact_id,
        hero_combo=combo,
        equity=result.equity,
        action_frequencies=[
            StrategyActionSnapshot(
                action=action.action,
                frequency=action.frequency,
                ev_chips=action.ev_chips,
                ev_loss_chips=action.ev_loss_chips,
            )
            for action in result.actions
        ],
        mismatch=resolution.match.distance,
        assumptions=result.assumptions,
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
    strategy = _replay_strategy(state)
    warnings = [
        "Synthetic replay only; no authorized live table is connected.",
        "GTO strategy is model-abstracted and limited to supported unopened preflop spots.",
        "Table control is disabled.",
    ]
    snapshot = MonitorSnapshot(
        generated_at=datetime.now(UTC),
        table_size=9,
        source_mode="synthetic_replay",
        state=state,
        action_history=history,
        health=MonitorHealth(
            status="degraded", strategy_status=strategy.status, warnings=warnings
        ),
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
        strategy=strategy,
        exploit=ExploitSnapshot(
            status="synthetic_only",
            confidence=0.0,
            sample_size=0,
            opponent_range_status="unavailable",
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
                "status": "passed" if strategy.status == "abstracted" else "blocked",
                "detail": (
                    "Configuration-matched model-abstracted GTO artifact resolved."
                    if strategy.status == "abstracted"
                    else "No supported GTO artifact resolved for this replay state."
                ),
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
