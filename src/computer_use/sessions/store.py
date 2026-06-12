"""SQLite persistence for Computer Use sessions."""

from __future__ import annotations

import json
import sqlite3
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
        self._init_db()

    def save(self, session: ComputerUseSession) -> None:
        payload = session.to_dict()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO computer_use_sessions (
                    id, goal, status, state_json, observations_json, actions_json,
                    created_at, updated_at, completed_at, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    goal=excluded.goal,
                    status=excluded.status,
                    state_json=excluded.state_json,
                    observations_json=excluded.observations_json,
                    actions_json=excluded.actions_json,
                    updated_at=excluded.updated_at,
                    completed_at=excluded.completed_at,
                    error=excluded.error
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
                ),
            )

    def get(self, session_id: str) -> ComputerUseSession | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                """
                SELECT id, goal, status, state_json, observations_json, actions_json,
                       created_at, updated_at, completed_at, error
                FROM computer_use_sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return ComputerUseSession(
            id=row[0],
            goal=row[1],
            status=ComputerUseStatus(row[2]),
            state=json.loads(row[3]),
            observations=json.loads(row[4]),
            actions=json.loads(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
            completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
            error=row[9],
        )

    def list_recent(self, *, limit: int = 20) -> list[ComputerUseSession]:
        with sqlite3.connect(self.path) as connection:
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
        with sqlite3.connect(self.path) as connection:
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
                )
                """
            )
