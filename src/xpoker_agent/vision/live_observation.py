"""Bounded continuous observation of one authorized X-Poker table."""

from __future__ import annotations

import asyncio
import hashlib
from collections import deque
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from typing import Literal

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.vision.live import diagnose_authorized_table
from xpoker_agent.vision.models import (
    DerivedActionCandidate,
    LiveCaptureDiagnostic,
    LiveObservationStatus,
    SeatActionConsensus,
    SeatStackConsensus,
    TemporalConsensus,
    TemporalSample,
)
from xpoker_agent.vision.temporal import consensus

CaptureCallable = Callable[
    [int, int], Awaitable[tuple[LiveCaptureDiagnostic, CapturedFrame]]
]


class TargetIdentityChanged(RuntimeError):
    pass


class LiveObservationService:
    def __init__(
        self,
        capture: CaptureCallable | None = None,
        *,
        maximum_samples: int = 30,
        maximum_consecutive_failures: int = 3,
    ) -> None:
        if maximum_samples < 3:
            raise ValueError("live observation requires at least three bounded samples")
        if maximum_consecutive_failures < 1:
            raise ValueError("failure threshold must be positive")
        self._capture = capture
        self._samples: deque[TemporalSample] = deque(maxlen=maximum_samples)
        self._pot_samples: deque[TemporalSample] = deque(maxlen=maximum_samples)
        self._board_samples: deque[TemporalSample] = deque(maxlen=maximum_samples)
        self._stack_samples: dict[int, deque[TemporalSample]] = {
            seat: deque(maxlen=maximum_samples) for seat in range(9)
        }
        self._action_samples: dict[int, deque[TemporalSample]] = {
            seat: deque(maxlen=maximum_samples) for seat in range(9)
        }
        self._maximum_consecutive_failures = maximum_consecutive_failures
        self._capture_lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._table_size: Literal[6, 9] = 9
        self._interval_ms = 500
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._latest_sequence = 0
        self._frames_attempted = 0
        self._frames_succeeded = 0
        self._frames_failed = 0
        self._consecutive_failures = 0
        self._session_target_fingerprint: str | None = None
        self._session_hwnd: int | None = None
        self._session_process_id: int | None = None
        self._target_stable = True
        self._last_error: str | None = None
        self._mode_consensus = TemporalConsensus(
            accepted=False,
            confidence=0.0,
            stable_frames=0,
            reason="no_samples",
        )
        self._pot_consensus = self._empty_consensus("no_samples")
        self._board_consensus = self._empty_consensus("no_samples")
        self._stack_consensus = [
            SeatStackConsensus(
                seat=seat,
                player_status="ambiguous",
                consensus=self._empty_consensus("no_samples"),
            )
            for seat in range(9)
        ]
        self._action_consensus = [
            SeatActionConsensus(
                seat=seat, consensus=self._empty_consensus("no_samples")
            )
            for seat in range(9)
        ]
        self._hand_epoch = 0
        self._last_accepted_board_count: int | None = None
        self._actions_armed = False
        self._emitted_action_keys: set[tuple[int, str, int, str]] = set()
        self._derived_actions: deque[DerivedActionCandidate] = deque(maxlen=50)
        self.latest_diagnostic: LiveCaptureDiagnostic | None = None
        self.latest_frame: CapturedFrame | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, *, table_size: Literal[6, 9], interval_ms: int) -> bool:
        if interval_ms < 1:
            raise ValueError("capture interval must be positive")
        if self.running:
            return False
        self._table_size = table_size
        self._interval_ms = interval_ms
        self._started_at = datetime.now(UTC)
        self._stopped_at = None
        self._latest_sequence = 0
        self._frames_attempted = 0
        self._frames_succeeded = 0
        self._frames_failed = 0
        self._consecutive_failures = 0
        self._session_target_fingerprint = None
        self._session_hwnd = None
        self._session_process_id = None
        self._target_stable = True
        self._last_error = None
        self._samples.clear()
        self._pot_samples.clear()
        self._board_samples.clear()
        for samples in self._stack_samples.values():
            samples.clear()
        for samples in self._action_samples.values():
            samples.clear()
        self._mode_consensus = TemporalConsensus(
            accepted=False,
            confidence=0.0,
            stable_frames=0,
            reason="no_samples",
        )
        self._pot_consensus = self._empty_consensus("no_samples")
        self._board_consensus = self._empty_consensus("no_samples")
        self._stack_consensus = [
            SeatStackConsensus(
                seat=seat,
                player_status="ambiguous",
                consensus=self._empty_consensus("no_samples"),
            )
            for seat in range(9)
        ]
        self._action_consensus = [
            SeatActionConsensus(
                seat=seat, consensus=self._empty_consensus("no_samples")
            )
            for seat in range(9)
        ]
        self._hand_epoch = 0
        self._last_accepted_board_count = None
        self._actions_armed = False
        self._emitted_action_keys.clear()
        self._derived_actions.clear()
        self.latest_diagnostic = None
        self.latest_frame = None
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="xpoker-live-observation")
        return True

    async def stop(self) -> bool:
        if not self.running:
            return False
        self._stop_event.set()
        assert self._task is not None
        await self._task
        return True

    async def inspect_once(
        self, *, table_size: Literal[6, 9]
    ) -> LiveCaptureDiagnostic:
        async with self._capture_lock:
            sequence = self._latest_sequence + 1
            self._frames_attempted += 1
            try:
                if self._capture is None:
                    diagnostic, frame = await diagnose_authorized_table(
                        table_size=table_size,
                        sequence=sequence,
                        locked_hwnd=self._session_hwnd,
                        locked_process_id=self._session_process_id,
                    )
                else:
                    diagnostic, frame = await self._capture(table_size, sequence)
                self._record_success(diagnostic, frame)
            except (OSError, RuntimeError, ValueError) as error:
                self._record_failure(error)
                raise
            return diagnostic

    def _record_success(
        self, diagnostic: LiveCaptureDiagnostic, frame: CapturedFrame
    ) -> None:
        if self._session_target_fingerprint is None:
            self._session_target_fingerprint = diagnostic.target_fingerprint
            self._session_hwnd = diagnostic.target_hwnd
            self._session_process_id = diagnostic.target_process_id
        elif diagnostic.target_fingerprint != self._session_target_fingerprint:
            self._target_stable = False
            raise TargetIdentityChanged("authorized X-Poker target identity changed during capture")
        self._latest_sequence = diagnostic.frame_sequence
        self._frames_succeeded += 1
        self._consecutive_failures = 0
        self._last_error = None
        self.latest_diagnostic = diagnostic
        self.latest_frame = frame
        if diagnostic.current_hand_mode == "ambiguous":
            self._samples.clear()
            self._mode_consensus = TemporalConsensus(
                accepted=False,
                confidence=0.0,
                stable_frames=0,
                reason="current_mode_ambiguous",
            )
        else:
            self._mode_consensus = self._append_consecutive(
                self._samples,
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=diagnostic.current_hand_mode,
                    confidence=diagnostic.rule_confidence,
                ),
            )
        self._record_numeric_observations(diagnostic)

    @staticmethod
    def _empty_consensus(reason: str) -> TemporalConsensus:
        return TemporalConsensus(
            accepted=False,
            confidence=0.0,
            stable_frames=0,
            reason=reason,
        )

    @staticmethod
    def _append_consecutive(
        samples: deque[TemporalSample], sample: TemporalSample
    ) -> TemporalConsensus:
        if samples and samples[-1].value != sample.value:
            samples.clear()
        samples.append(sample)
        return consensus(list(samples))

    def _record_numeric_observations(self, diagnostic: LiveCaptureDiagnostic) -> None:
        if not diagnostic.board_geometry_supported or diagnostic.board_card_slots not in {
            0,
            3,
            4,
            5,
        }:
            self._board_samples.clear()
            self._board_consensus = self._empty_consensus("current_board_ambiguous")
        else:
            self._board_consensus = self._append_consecutive(
                self._board_samples,
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=str(diagnostic.board_card_slots),
                    confidence=max(0.9, diagnostic.board_geometry_confidence),
                ),
            )
            if self._board_consensus.accepted:
                board_count = int(self._board_consensus.value or "0")
                if (
                    self._last_accepted_board_count is not None
                    and self._last_accepted_board_count >= 3
                    and board_count == 0
                ):
                    self._hand_epoch += 1
                    self._actions_armed = False
                self._last_accepted_board_count = board_count

        if diagnostic.pot.value_native is None:
            self._pot_samples.clear()
            self._pot_consensus = self._empty_consensus("current_pot_ambiguous")
        else:
            self._pot_consensus = self._append_consecutive(
                self._pot_samples,
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=str(diagnostic.pot.value_native),
                    confidence=diagnostic.pot.confidence,
                ),
            )

        by_seat = {panel.seat: panel for panel in diagnostic.seat_panels}
        stack_consensus: list[SeatStackConsensus] = []
        for seat in range(diagnostic.table_size):
            panel = by_seat.get(seat)
            samples = self._stack_samples[seat]
            if panel is None or panel.stack_native is None or panel.status != "seated":
                samples.clear()
                state = panel.status if panel is not None else "ambiguous"
                result = self._empty_consensus("current_stack_ambiguous")
            else:
                state = panel.status
                result = self._append_consecutive(
                    samples,
                    TemporalSample(
                        frame_sequence=diagnostic.frame_sequence,
                        content_sha256=diagnostic.content_sha256,
                        value=str(panel.stack_native),
                        confidence=panel.confidence,
                    ),
                )
            stack_consensus.append(
                SeatStackConsensus(seat=seat, player_status=state, consensus=result)
            )
        self._stack_consensus = stack_consensus
        by_action_seat = {action.seat: action for action in diagnostic.seat_actions}
        action_consensus: list[SeatActionConsensus] = []
        for seat in range(diagnostic.table_size):
            observation = by_action_seat.get(seat)
            samples = self._action_samples[seat]
            if observation is None or observation.action is None:
                samples.clear()
                result = self._empty_consensus("current_action_absent")
            else:
                result = self._append_consecutive(
                    samples,
                    TemporalSample(
                        frame_sequence=diagnostic.frame_sequence,
                        content_sha256=diagnostic.content_sha256,
                        value=observation.action,
                        confidence=observation.confidence,
                    ),
                )
            action_consensus.append(SeatActionConsensus(seat=seat, consensus=result))
        self._action_consensus = action_consensus
        visible_actions = [
            action for action in diagnostic.seat_actions if action.action is not None
        ]
        if not visible_actions:
            self._actions_armed = True
        if (
            self._actions_armed
            and self._board_consensus.accepted
            and self._mode_consensus.accepted
        ):
            street_by_cards = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
            street = street_by_cards.get(int(self._board_consensus.value or "-1"))
            if street is not None:
                for action in action_consensus:
                    result = action.consensus
                    if not result.accepted or result.value is None:
                        continue
                    key = (self._hand_epoch, street, action.seat, result.value)
                    if key in self._emitted_action_keys:
                        continue
                    encoded = (
                        f"{diagnostic.target_fingerprint}:{self._hand_epoch}:"
                        f"{street}:{action.seat}:{result.value}"
                    ).encode()
                    self._derived_actions.append(
                        DerivedActionCandidate(
                            event_id=hashlib.sha256(encoded).hexdigest(),
                            hand_epoch=self._hand_epoch,
                            frame_sequence=diagnostic.frame_sequence,
                            seat=action.seat,
                            street=street,
                            action=result.value,
                            confidence=result.confidence,
                        )
                    )
                    self._emitted_action_keys.add(key)

    def _record_failure(self, error: Exception) -> None:
        self._frames_failed += 1
        self._consecutive_failures += 1
        self._last_error = str(error)

    async def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    await self.inspect_once(table_size=self._table_size)
                except TargetIdentityChanged:
                    break
                except (OSError, RuntimeError, ValueError):
                    if self._consecutive_failures >= self._maximum_consecutive_failures:
                        break
                with suppress(TimeoutError):
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self._interval_ms / 1000
                    )
        finally:
            self._stopped_at = datetime.now(UTC)

    def status(self) -> LiveObservationStatus:
        latest_at = self.latest_diagnostic.captured_at if self.latest_diagnostic else None
        latest_age_ms = None
        if latest_at is not None:
            latest_age_ms = max(0.0, (datetime.now(UTC) - latest_at).total_seconds() * 1000)
        return LiveObservationStatus(
            running=self.running,
            table_size=self._table_size,
            interval_ms=self._interval_ms,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            latest_sequence=self._latest_sequence,
            frames_attempted=self._frames_attempted,
            frames_succeeded=self._frames_succeeded,
            frames_failed=self._frames_failed,
            consecutive_failures=self._consecutive_failures,
            latest_captured_at=latest_at,
            latest_age_ms=latest_age_ms,
            target_fingerprint=self._session_target_fingerprint,
            target_stable=self._target_stable,
            current_hand_mode=(
                self.latest_diagnostic.current_hand_mode
                if self.latest_diagnostic
                else "ambiguous"
            ),
            current_hand_supported=(
                self.latest_diagnostic.current_hand_supported
                if self.latest_diagnostic
                else False
            ),
            mode_consensus=self._mode_consensus,
            board_consensus=self._board_consensus,
            pot_consensus=self._pot_consensus,
            seat_stack_consensus=self._stack_consensus,
            seat_action_consensus=self._action_consensus,
            hand_epoch=self._hand_epoch,
            derived_action_candidates=list(self._derived_actions),
            last_error=self._last_error,
        )
