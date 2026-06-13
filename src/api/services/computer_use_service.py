from __future__ import annotations

import asyncio
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.api.schemas.events import EventEnvelope
from src.api.services.event_service import EventBus as ApiEventBus
from src.computer_use import ComputerUseEngine
from src.computer_use.capabilities import require_capability
from src.computer_use.models import ComputerUseStatus, PlanStep
from src.computer_use.sessions import ComputerUseSessionStore
from src.config import PROJECT_ROOT


class ComputerUseService:
    def __init__(self, *, engine: ComputerUseEngine | None = None, events: ApiEventBus | None = None):
        store_path = Path(os.getenv(
            "COMPUTER_USE_SESSIONS_PATH",
            str(Path(PROJECT_ROOT) / "data" / "computer_use.sqlite3"),
        ))
        self.engine = engine or ComputerUseEngine(session_store=ComputerUseSessionStore(store_path))
        self.events = events
        self._background: dict[str, asyncio.Task] = {}
        self.engine.runtime.event_bus.subscribe(None, self._forward_event)

    async def _ensure_runtime(self) -> None:
        await self.engine.runtime.event_bus.start()

    async def _forward_event(self, event) -> None:
        if self.events is None:
            return
        data = dict(event.payload)
        session_id = data.get("session_id")
        session = self.engine.session_store.get(session_id) if session_id else None
        data.update({
            "session_id": session_id,
            "correlation_id": session.correlation_id if session else None,
            "timestamp": event.created_at.isoformat(),
            "status": session.status.value if session else data.get("status", "unknown"),
            "safe_summary": _safe_summary(event.event_type.value, data),
            "current_step": session.current_step_index if session else 0,
            "risk_level": "high" if "confirmation" in event.event_type.value else "low",
        })
        allowed = {
            "session_id", "correlation_id", "timestamp", "status",
            "safe_summary", "current_step", "risk_level",
        }
        await self.events.publish(EventEnvelope(
            type=event.event_type.value,
            data={key: data.get(key) for key in allowed},
            correlation_id=data.get("correlation_id"),
        ))

    async def run(self, goal: str, *, max_iterations: int = 3) -> dict[str, Any]:
        await self._ensure_runtime()
        return (await self.engine.run_goal(goal, max_iterations=max_iterations)).to_dict()

    async def create(self, goal: str) -> dict[str, Any]:
        await self._ensure_runtime()
        return self.engine.create_session(goal).to_dict()

    async def run_session(self, session_id: str, *, max_iterations: int = 3) -> dict[str, Any]:
        await self._ensure_runtime()
        return (await self.engine.run_session(session_id, max_iterations=max_iterations)).to_dict()

    async def observe(self, *, include_ocr: bool = False) -> dict[str, Any]:
        return (await self.engine.observe(include_ocr=include_ocr)).to_dict()

    def observe_window(self, *, window_handle: int | None, include_ocr: bool) -> dict[str, Any]:
        return self.engine.observer.observe_window(window_handle, include_ocr=include_ocr).to_dict()

    def find_control(self, query: str, *, window_handle: int | None) -> dict[str, Any]:
        controls = self.engine.observer.ui_automation.find_controls(
            window_handle=window_handle, query=query, limit=20
        )
        return {
            "count": len(controls),
            "controls": [asdict(item) for item in controls if not item.is_password],
            "uia_available": self.engine.observer.ui_automation.available,
        }

    async def execute_capability(
        self, capability: str, arguments: dict[str, Any], *, session_id: str | None, approved: bool
    ) -> dict[str, Any]:
        definition = require_capability(capability)
        session = self.engine.session_store.get(session_id) if session_id else None
        if session is None:
            session = self.engine.create_session(f"Ejecutar {capability}")
        token = self.engine.confirm(session.id, capability) if approved else None
        result = await self.engine.executor.execute_step(
            PlanStep(capability, f"Ejecutar {capability}", args=arguments),
            session_id=session.id,
            confirmation_token=token,
        )
        session.policy_decisions.append(result.get("policy", {}))
        session.record_action({"capability": capability, "result": result})
        if result.get("policy", {}).get("requires_confirmation") and not result["ok"]:
            session.transition(ComputerUseStatus.RUNNING)
            session.transition(ComputerUseStatus.WAITING_CONFIRMATION)
            session.state["pending_confirmation"] = {
                "capability": capability, "description": f"Ejecutar {capability}",
                "risk_level": "high", "arguments": _redact(arguments), "source": "capability",
            }
        elif result["ok"]:
            session.transition(ComputerUseStatus.RUNNING)
            session.transition(ComputerUseStatus.COMPLETED)
        else:
            session.transition(ComputerUseStatus.RUNNING)
            session.transition(ComputerUseStatus.FAILED, error=result.get("error"))
        self.engine.session_store.save(session)
        return {"ok": result["ok"], "session": session.to_dict(), "result": result}

    async def confirm(self, session_id: str, approved: bool) -> dict[str, Any]:
        session = self.engine.session_store.get(session_id)
        if session is None:
            raise KeyError("Sesion Computer Use no encontrada.")
        pending = session.state.get("pending_confirmation") or {}
        capability = pending.get("capability")
        if session.status != ComputerUseStatus.WAITING_CONFIRMATION or not capability:
            raise ValueError("La sesion no tiene una confirmacion pendiente.")
        if not approved:
            self.engine.cancel(session_id)
            return {"approved": False, "session_id": session_id, "session": self.get_session(session_id)}
        if pending.get("source") == "capability":
            result = await self.execute_capability(
                capability,
                pending.get("arguments", {}),
                session_id=session_id,
                approved=True,
            )
            return {"approved": True, "session_id": session_id, "session": result["session"]}
        token = self.engine.confirm(session_id, capability)
        session.state.pop("pending_confirmation", None)
        self.engine.session_store.save(session)
        updated = await self.engine.run_session(
            session_id, confirmation_tokens={capability: token}
        )
        return {"approved": True, "session_id": session_id, "session": updated.to_dict()}

    def list_sessions(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return [session.to_dict() for session in self.engine.session_store.list_recent(limit=limit)]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.engine.session_store.get(session_id)
        return session.to_dict() if session else None

    def cancel(self, session_id: str) -> bool:
        return self.engine.cancel(session_id)

    def status(self) -> dict[str, Any]:
        recent = self.engine.session_store.list_recent(limit=100)
        return {
            "available": True,
            "ui_automation": self.engine.observer.ui_automation.available,
            "active_sessions": sum(
                item.status in {ComputerUseStatus.CREATED, ComputerUseStatus.RUNNING, ComputerUseStatus.WAITING_CONFIRMATION}
                for item in recent
            ),
        }


def _safe_summary(event_type: str, data: dict[str, Any]) -> str:
    summaries = {
        "computer_use.started": "Sesion Computer Use iniciada.",
        "computer_use.observed": "Observacion completada.",
        "computer_use.planned": "Plan creado.",
        "computer_use.executed": "Paso ejecutado.",
        "computer_use.verified": "Resultado verificado.",
        "computer_use.confirmation_required": "Confirmacion del usuario requerida.",
        "computer_use.cancelled": "Sesion cancelada.",
        "computer_use.completed": "Sesion completada.",
        "computer_use.failed": "La sesion no pudo completarse.",
    }
    return summaries.get(event_type, "Actualizacion de Computer Use.")


def _redact(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        key: "[redacted]" if any(word in key.lower() for word in ("password", "secret", "token")) else value
        for key, value in arguments.items()
    }
