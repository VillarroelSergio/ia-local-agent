"""Observe-plan-act-verify loop for Computer Use."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import asyncio

try:
    from computer_use.executor import ComputerUseExecutor
    from computer_use.models import ComputerUseSession, ComputerUseStatus
    from computer_use.observer import DesktopObserver
    from computer_use.planner import ComputerUsePlanner
    from computer_use.sessions import ComputerUseSessionStore
    from computer_use.state import ComputerStateManager
    from computer_use.verifier import ResultVerifier
    from config import PROJECT_ROOT
    from os_integration.events import EventBus, EventPriority, EventType, OSEvent
    from os_integration.lifecycle import WindowsIntegrationRuntime
except ModuleNotFoundError:
    from src.computer_use.executor import ComputerUseExecutor
    from src.computer_use.models import ComputerUseSession, ComputerUseStatus
    from src.computer_use.observer import DesktopObserver
    from src.computer_use.planner import ComputerUsePlanner
    from src.computer_use.sessions import ComputerUseSessionStore
    from src.computer_use.state import ComputerStateManager
    from src.computer_use.verifier import ResultVerifier
    from src.config import PROJECT_ROOT
    from src.os_integration.events import EventBus, EventPriority, EventType, OSEvent
    from src.os_integration.lifecycle import WindowsIntegrationRuntime


class ComputerUseEngine:
    def __init__(
        self,
        *,
        runtime: WindowsIntegrationRuntime | None = None,
        observer: DesktopObserver | None = None,
        planner: ComputerUsePlanner | None = None,
        verifier: ResultVerifier | None = None,
        state_manager: ComputerStateManager | None = None,
        session_store: ComputerUseSessionStore | None = None,
        max_iterations: int = 3,
    ):
        self.runtime = runtime or WindowsIntegrationRuntime.build()
        self.observer = observer or DesktopObserver(
            window_manager=self.runtime.window_manager,
            ocr_service=self.runtime.ocr_service,
            security=self.runtime.security,
        )
        self.planner = planner or ComputerUsePlanner()
        self.verifier = verifier or ResultVerifier()
        self.state_manager = state_manager or ComputerStateManager()
        self.executor = ComputerUseExecutor(self.runtime.workflow_runner, security=self.runtime.security)
        self.session_store = session_store or ComputerUseSessionStore(Path(PROJECT_ROOT) / "data" / "computer_use.sqlite3")
        self.max_iterations = max_iterations
        self._cancel_events: dict[str, asyncio.Event] = {}

    async def run_goal(self, goal: str, *, max_iterations: int | None = None) -> ComputerUseSession:
        session = ComputerUseSession(goal=goal, status=ComputerUseStatus.RUNNING)
        self._cancel_events[session.id] = asyncio.Event()
        self.session_store.save(session)
        await self._publish(EventType.COMPUTER_USE_STARTED, {"session_id": session.id, "goal": goal})
        limit = max_iterations or self.max_iterations
        try:
            for iteration in range(limit):
                if self._cancel_events[session.id].is_set():
                    session.status = ComputerUseStatus.CANCELLED
                    session.error = "cancelled"
                    await self._publish(EventType.COMPUTER_USE_FAILED, {
                        "session_id": session.id,
                        "error": session.error,
                    }, priority=EventPriority.HIGH)
                    break
                observation = self.observer.observe_desktop(include_ocr=False)
                session.record_observation(observation)
                changes = self.state_manager.update_observation(observation)
                await self._publish(EventType.COMPUTER_USE_OBSERVED, {
                    "session_id": session.id,
                    "iteration": iteration,
                    "changes": changes,
                    "summary": observation.screen_summary,
                })

                plan = self.planner.create_plan(goal, observation)
                graph = self.planner.execution_graph(plan)
                session.state.update({"plan": plan.id, "graph": graph.metadata, "iteration": iteration})
                await self._publish(EventType.COMPUTER_USE_PLANNED, {
                    "session_id": session.id,
                    "plan_id": plan.id,
                    "steps": [step.description for step in plan.steps],
                })

                execution = await self.executor.execute_plan(plan)
                session.record_action({"plan_id": plan.id, "execution": execution})
                await self._publish(EventType.COMPUTER_USE_EXECUTED, {
                    "session_id": session.id,
                    "plan_id": plan.id,
                    "ok": execution["ok"],
                })

                refreshed = self.observer.observe_desktop(include_ocr=False)
                verification = self.verifier.verify_goal(goal, refreshed)
                session.record_action({"verification": verification})
                await self._publish(EventType.COMPUTER_USE_VERIFIED, {
                    "session_id": session.id,
                    "ok": verification["ok"],
                    "reason": verification["reason"],
                })

                if execution["ok"] and verification["ok"]:
                    session.status = ComputerUseStatus.COMPLETED
                    session.completed_at = datetime.now()
                    await self._publish(EventType.COMPUTER_USE_COMPLETED, {"session_id": session.id})
                    break
            else:
                session.status = ComputerUseStatus.ABORTED
                session.error = "iteration_limit_exceeded"
                await self._publish(EventType.COMPUTER_USE_FAILED, {
                    "session_id": session.id,
                    "error": session.error,
                }, priority=EventPriority.HIGH)
        except Exception as error:
            session.status = ComputerUseStatus.FAILED
            session.error = str(error)
            await self._publish(EventType.COMPUTER_USE_FAILED, {
                "session_id": session.id,
                "error": session.error,
            }, priority=EventPriority.HIGH)
        finally:
            session.updated_at = datetime.now()
            self.session_store.save(session)
            self._cancel_events.pop(session.id, None)
        return session

    async def observe(self, *, include_ocr: bool = False):
        observation = self.observer.observe_desktop(include_ocr=include_ocr)
        self.state_manager.update_observation(observation)
        return observation

    def cancel(self, session_id: str) -> bool:
        cancel_event = self._cancel_events.get(session_id)
        if cancel_event is None:
            return False
        cancel_event.set()
        self.runtime.workflow_runner.cancel(session_id)
        return True

    async def _publish(self, event_type: EventType, payload: dict, *, priority: EventPriority = EventPriority.NORMAL) -> None:
        event_bus: EventBus = self.runtime.event_bus
        await event_bus.publish(OSEvent(event_type, payload, priority=priority, source="computer_use"))
