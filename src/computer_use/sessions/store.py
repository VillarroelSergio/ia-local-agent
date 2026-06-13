"""SQLite persistence for Computer Use sessions."""

from __future__ import annotations

import json
import sqlite3
from threading import RLock
from datetime import datetime
from pathlib import Path

try:
    from computer_use.models import ComputerUseSession, ComputerUseStatus
except ModuleNotFoundError:
    from src.computer_use.models import ComputerUseSession, ComputerUseStatus


class ComputerUseSessionStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def save(self, session: ComputerUseSession) -> None:
        payload = session.to_dict()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO computer_use_sessions (
                    id, goal, status, state_json, observations_json, actions_json,
                    created_at, updated_at, completed_at, error, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    goal=excluded.goal,
                    status=excluded.status,
                    state_json=excluded.state_json,
                    observations_json=excluded.observations_json,
                    actions_json=excluded.actions_json,
                    updated_at=excluded.updated_at,
                    completed_at=excluded.completed_at,
                    error=excluded.error,
                    payload_json=excluded.payload_json
                """,
                (
                    session.id,
                    session.goal,
                    session.status.value,
                    json.dumps(payload["state"], ensure_ascii=False),
                    json.dumps(payload["observations"], ensure_ascii=False),
                    json.dumps(payload["actions"], ensure_ascii=False),
                    payload["created_at"],
                    payload["updated_at"],
                    payload["completed_at"],
                    session.error,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def get(self, session_id: str) -> ComputerUseSession | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, goal, status, state_json, observations_json, actions_json,
                       created_at, updated_at, completed_at, error, payload_json
                FROM computer_use_sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        if row[10]:
            return self._from_payload(self._load_json(row[10], {}))
        return ComputerUseSession(
            id=row[0],
            goal=row[1],
            status=ComputerUseStatus(row[2]),
            state=self._load_json(row[3], {}),
            observations=self._load_json(row[4], []),
            actions=self._load_json(row[5], []),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
            completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
            error=row[9],
        )

    def list_recent(self, *, limit: int = 20) -> list[ComputerUseSession]:
        limit = max(0, min(int(limit), 200))
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id FROM computer_use_sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [session for row in rows if (session := self.get(row[0])) is not None]

    def _init_db(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS computer_use_sessions (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    observations_json TEXT NOT NULL,
                    actions_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    error TEXT
                    , payload_json TEXT
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(computer_use_sessions)")}
            migrations = {
                "state_json": "TEXT NOT NULL DEFAULT '{}'",
                "observations_json": "TEXT NOT NULL DEFAULT '[]'",
                "actions_json": "TEXT NOT NULL DEFAULT '[]'",
                "completed_at": "TEXT",
                "error": "TEXT",
                "payload_json": "TEXT",
            }
            for name, definition in migrations.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE computer_use_sessions ADD COLUMN {name} {definition}")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_computer_use_sessions_updated_at "
                "ON computer_use_sessions(updated_at DESC)"
            )

    @staticmethod
    def _load_json(value: str | None, default):
        try:
            loaded = json.loads(value) if value else default
        except (TypeError, json.JSONDecodeError):
            return default
        return loaded if isinstance(loaded, type(default)) else default

    @staticmethod
    def _from_payload(payload: dict) -> ComputerUseSession:
        values = dict(payload)
        values["status"] = ComputerUseStatus(values["status"])
        for key in ("created_at", "updated_at", "completed_at", "cancelled_at"):
            if values.get(key):
                values[key] = datetime.fromisoformat(values[key])
        return ComputerUseSession(**values)

    def create(self, session: ComputerUseSession) -> ComputerUseSession:
        self.save(session)
        return session

    def list(self, *, limit: int = 20) -> list[ComputerUseSession]:
        return self.list_recent(limit=limit)

    def update_status(self, session_id: str, status: ComputerUseStatus) -> ComputerUseSession | None:
        session = self.get(session_id)
        if session:
            session.transition(status)
            self.save(session)
        return session

    def append_observation(self, session_id: str, observation) -> ComputerUseSession | None:
        session = self.get(session_id)
        if session:
            session.record_observation(observation)
            self.save(session)
        return session

    def append_action(self, session_id: str, action: dict) -> ComputerUseSession | None:
        session = self.get(session_id)
        if session:
            session.record_action(action)
            self.save(session)
        return session

    def append_verification(self, session_id: str, verification: dict) -> ComputerUseSession | None:
        session = self.get(session_id)
        if session:
            session.record_verification(verification)
            self.save(session)
        return session

    def append_error(self, session_id: str, error: str) -> ComputerUseSession | None:
        session = self.get(session_id)
        if session:
            session.record_error(error)
            self.save(session)
        return session

    def cancel(self, session_id: str) -> ComputerUseSession | None:
        session = self.get(session_id)
        if session and session.status not in {
            ComputerUseStatus.COMPLETED,
            ComputerUseStatus.FAILED,
            ComputerUseStatus.ABORTED,
            ComputerUseStatus.CANCELLED,
        }:
            session.transition(ComputerUseStatus.CANCELLED, error="cancelled")
            self.save(session)
        return session


ComputerUseSessionRepository = ComputerUseSessionStore
