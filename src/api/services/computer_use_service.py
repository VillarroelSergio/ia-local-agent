from __future__ import annotations

from pathlib import Path
import os
from typing import Any

from src.computer_use import ComputerUseEngine
from src.computer_use.sessions import ComputerUseSessionStore
from src.config import PROJECT_ROOT


class ComputerUseService:
    def __init__(self, *, engine: ComputerUseEngine | None = None):
        store_path = Path(os.getenv("COMPUTER_USE_SESSIONS_PATH", str(Path(PROJECT_ROOT) / "data" / "computer_use.sqlite3")))
        self.engine = engine or ComputerUseEngine(
            session_store=ComputerUseSessionStore(store_path)
        )

    async def run(self, goal: str, *, max_iterations: int = 3) -> dict[str, Any]:
        session = await self.engine.run_goal(goal, max_iterations=max_iterations)
        return session.to_dict()

    async def observe(self, *, include_ocr: bool = False) -> dict[str, Any]:
        observation = await self.engine.observe(include_ocr=include_ocr)
        return observation.to_dict()

    def list_sessions(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return [session.to_dict() for session in self.engine.session_store.list_recent(limit=limit)]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.engine.session_store.get(session_id)
        return session.to_dict() if session else None

    def cancel(self, session_id: str) -> bool:
        return self.engine.cancel(session_id)
