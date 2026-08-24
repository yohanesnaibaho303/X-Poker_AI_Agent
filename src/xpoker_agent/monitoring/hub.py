"""Bounded monitor stream with retained history and explicit gap recovery."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import UTC, datetime

from xpoker_agent.monitoring.models import MonitorEnvelope, MonitorHistory, MonitorSnapshot


class MonitorHub:
    def __init__(self, *, history_limit: int = 512, subscriber_queue_size: int = 64) -> None:
        if history_limit < 2 or subscriber_queue_size < 1:
            raise ValueError("monitor history and subscriber queue limits must be positive")
        self._history: deque[MonitorEnvelope] = deque(maxlen=history_limit)
        self._subscriber_queue_size = subscriber_queue_size
        self._subscribers: set[asyncio.Queue[MonitorEnvelope]] = set()
        self._sequence = 0
        self._dropped_deliveries = 0
        self._snapshot: MonitorSnapshot | None = None
        self._lock = asyncio.Lock()

    @property
    def latest_sequence(self) -> int:
        return self._sequence

    @property
    def dropped_deliveries(self) -> int:
        return self._dropped_deliveries

    @property
    def snapshot(self) -> MonitorSnapshot | None:
        return self._snapshot.model_copy(deep=True) if self._snapshot is not None else None

    async def publish(
        self,
        kind: str,
        payload: dict[str, object],
        *,
        snapshot: MonitorSnapshot | None = None,
    ) -> MonitorEnvelope:
        async with self._lock:
            self._sequence += 1
            drop_count = sum(queue.full() for queue in self._subscribers)
            self._dropped_deliveries += drop_count
            normalized_payload = payload
            if snapshot is not None:
                self._snapshot = snapshot.model_copy(
                    deep=True,
                    update={
                        "sequence": self._sequence,
                        "metrics": snapshot.metrics.model_copy(
                            update={
                                "stream_sequence": self._sequence,
                                "dropped_deliveries": self._dropped_deliveries,
                            }
                        ),
                    },
                )
                serialized_snapshot = self._snapshot.model_dump(mode="json")
                if kind == "snapshot":
                    normalized_payload = serialized_snapshot
                elif "snapshot" in payload:
                    normalized_payload = {**payload, "snapshot": serialized_snapshot}
            envelope = MonitorEnvelope(
                sequence=self._sequence,
                kind=kind,
                emitted_at=datetime.now(UTC),
                payload=normalized_payload,
            )
            self._history.append(envelope)
            for queue in self._subscribers:
                if queue.full():
                    queue.get_nowait()
                queue.put_nowait(envelope)
            return envelope

    async def publish_snapshot(self, snapshot: MonitorSnapshot) -> MonitorEnvelope:
        return await self.publish(
            "snapshot",
            snapshot.model_dump(mode="json"),
            snapshot=snapshot,
        )

    async def subscribe(self) -> asyncio.Queue[MonitorEnvelope]:
        queue: asyncio.Queue[MonitorEnvelope] = asyncio.Queue(maxsize=self._subscriber_queue_size)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[MonitorEnvelope]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    def history_after(self, after_sequence: int) -> MonitorHistory:
        if after_sequence < 0:
            raise ValueError("after_sequence cannot be negative")
        oldest = self._history[0].sequence if self._history else self._sequence + 1
        gap_required = bool(self._history) and after_sequence < oldest - 1
        envelopes = (
            []
            if gap_required
            else [item for item in self._history if item.sequence > after_sequence]
        )
        return MonitorHistory(
            after_sequence=after_sequence,
            latest_sequence=self._sequence,
            gap_required=gap_required,
            envelopes=envelopes,
        )
