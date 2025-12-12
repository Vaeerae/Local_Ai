"""SQLite-backed append-only event store."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from orchestrator.events import EventRecord


class EventStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def append(self, event: EventRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO events (event_id, event_type, created_at, payload)
                VALUES (?, ?, ?, ?);
                """,
                (
                    event.event_id,
                    event.event_type.value,
                    event.created_at.isoformat(),
                    json.dumps(event.payload, default=str),
                ),
            )
            conn.commit()

    def fetch_all(self) -> Iterable[EventRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT event_id, event_type, created_at, payload FROM events ORDER BY created_at;"
            )
            rows = cursor.fetchall()
            for event_id, event_type, created_at, payload in rows:
                yield EventRecord(
                    event_id=event_id,
                    event_type=event_type,
                    created_at=created_at,
                    payload=json.loads(payload),
                )

    def last(self) -> Optional[EventRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT event_id, event_type, created_at, payload FROM events ORDER BY created_at DESC LIMIT 1;"
            )
            row = cursor.fetchone()
            if not row:
                return None
            event_id, event_type, created_at, payload = row
            return EventRecord(
                event_id=event_id,
                event_type=event_type,
                created_at=created_at,
                payload=json.loads(payload),
            )
