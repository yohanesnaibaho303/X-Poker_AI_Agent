"""Bounded continuous observation of one authorized X-Poker table."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from typing import Literal

from xpoker_agent.capture.frames import CapturedFrame
from xpoker_agent.vision.live import diagnose_authorized_table
from xpoker_agent.vision.models import (
    LiveCaptureDiagnostic,
    LiveObservationStatus,
    TemporalConsensus,
    TemporalSample,
)
from xpoker_agent.vision.temporal import consensus

CaptureCallable = Callable[
    [int, int], Awaitable[tuple[LiveCaptureDiagnostic, CapturedFrame]]
]


async def _default_capture(
    table_size: int, sequence: int
) -> tuple[LiveCaptureDiagnostic, CapturedFrame]:
    return await diagnose_authorized_table(table_size=table_size, sequence=sequence)


class TargetIdentityChanged(RuntimeError):
    pass


class LiveObservationService:
    def __init__(
        self,
        capture: CaptureCallable = _default_capture,
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
        self._target_stable = True
        self._last_error: str | None = None
        self._mode_consensus = TemporalConsensus(
            accepted=False,
            confidence=0.0,
            stable_frames=0,
            reason="no_samples",
        )
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
        self._target_stable = True
        self._last_error = None
        self._samples.clear()
        self._mode_consensus = TemporalConsensus(
            accepted=False,
            confidence=0.0,
            stable_frames=0,
            reason="no_samples",
        )
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
            self._samples.append(
                TemporalSample(
                    frame_sequence=diagnostic.frame_sequence,
                    content_sha256=diagnostic.content_sha256,
                    value=diagnostic.current_hand_mode,
                    confidence=diagnostic.rule_confidence,
                )
            )
            self._mode_consensus = consensus(list(self._samples))

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
            last_error=self._last_error,
        )
