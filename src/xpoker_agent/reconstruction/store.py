"""SQLite-backed append-only, hash-chained canonical hand event storage."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

from xpoker_agent.models import HandEvent

_GENESIS_HASH = "0" * 64


class EventStoreError(RuntimeError):
    """Raised when an event log violates append-only or integrity constraints."""


class AppendOnlyEventStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def __enter__(self) -> AppendOnlyEventStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS hand_events (
                hand_id TEXT NOT NULL,
                sequence INTEGER NOT NULL CHECK (sequence >= 1),
                event_id TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE,
                appended_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                PRIMARY KEY (hand_id, sequence)
            );
            CREATE TRIGGER IF NOT EXISTS hand_events_no_update
            BEFORE UPDATE ON hand_events
            BEGIN
                SELECT RAISE(ABORT, 'hand_events is append-only');
            END;
            CREATE TRIGGER IF NOT EXISTS hand_events_no_delete
            BEFORE DELETE ON hand_events
            BEGIN
                SELECT RAISE(ABORT, 'hand_events is append-only');
            END;
            """
        )
        self._connection.commit()

    @staticmethod
    def _canonical_payload(event: HandEvent) -> str:
        return json.dumps(
            event.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _event_hash(previous_hash: str, payload: str) -> str:
        return hashlib.sha256(f"{previous_hash}:{payload}".encode()).hexdigest()

    def append(self, event: HandEvent) -> str:
        try:
            with self._connection:
                return self._append_without_commit(event)
        except sqlite3.IntegrityError as error:
            raise EventStoreError(f"event append rejected: {error}") from error

    def _append_without_commit(self, event: HandEvent) -> str:
        row = self._connection.execute(
            "SELECT sequence, event_hash FROM hand_events WHERE hand_id = ? "
            "ORDER BY sequence DESC LIMIT 1",
            (str(event.hand_id),),
        ).fetchone()
        expected_sequence = 1 if row is None else int(row["sequence"]) + 1
        if event.sequence != expected_sequence:
            raise EventStoreError(
                f"expected event sequence {expected_sequence}, got {event.sequence}"
            )
        previous_hash = _GENESIS_HASH if row is None else str(row["event_hash"])
        payload = self._canonical_payload(event)
        event_hash = self._event_hash(previous_hash, payload)
        self._connection.execute(
            "INSERT INTO hand_events "
            "(hand_id, sequence, event_id, payload_json, previous_hash, event_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(event.hand_id),
                event.sequence,
                str(event.event_id),
                payload,
                previous_hash,
                event_hash,
            ),
        )
        return event_hash

    def append_many(self, events: Iterable[HandEvent]) -> list[str]:
        hashes: list[str] = []
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            for event in events:
                hashes.append(self._append_without_commit(event))
            self._connection.commit()
        except EventStoreError:
            self._connection.rollback()
            raise
        except sqlite3.IntegrityError as error:
            self._connection.rollback()
            raise EventStoreError(f"event batch append rejected: {error}") from error
        return hashes

    def load_hand(self, hand_id: UUID) -> list[HandEvent]:
        rows = self._connection.execute(
            "SELECT payload_json FROM hand_events WHERE hand_id = ? ORDER BY sequence",
            (str(hand_id),),
        ).fetchall()
        return [HandEvent.model_validate_json(row["payload_json"]) for row in rows]

    def verify_hand(self, hand_id: UUID) -> list[str]:
        rows = self._connection.execute(
            "SELECT sequence, payload_json, previous_hash, event_hash FROM hand_events "
            "WHERE hand_id = ? ORDER BY sequence",
            (str(hand_id),),
        ).fetchall()
        issues: list[str] = []
        previous_hash = _GENESIS_HASH
        for expected_sequence, row in enumerate(rows, start=1):
            if row["sequence"] != expected_sequence:
                issues.append(f"non_contiguous_sequence:{row['sequence']}")
            if row["previous_hash"] != previous_hash:
                issues.append(f"previous_hash_mismatch:{row['sequence']}")
            calculated = self._event_hash(previous_hash, row["payload_json"])
            if row["event_hash"] != calculated:
                issues.append(f"event_hash_mismatch:{row['sequence']}")
            previous_hash = row["event_hash"]
        return issues
