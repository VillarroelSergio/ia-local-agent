"""Observe-plan-act-verify loop for Computer Use."""

from __future__ import annotations

from pathlib import Path
import asyncio

try:
    from computer_use.executor import ComputerUseExecutor
    from computer_use.capabilities import ConfirmationStore
    from computer_use.models import ComputerUseSession, ComputerUseStatus, TERMINAL_STATUSES
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
    from src.computer_use.capabilities import ConfirmationStore
    from src.computer_use.models import ComputerUseSession, ComputerUseStatus, TERMINAL_STATUSES
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
        self.confirmations = ConfirmationStore()
        self.executor = ComputerUseExecutor(
            self.runtime.workflow_runner,
            security=self.runtime.security,
            confirmations=self.confirmations,
            ui_automation=self.observer.ui_automation,
        )
        self.session_store = session_store or ComputerUseSessionStore(Path(PROJECT_ROOT) / "data" / "computer_use.sqlite3")
        self.max_iterations = max_iterations
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def create_session(self, goal: str) -> ComputerUseSession:
        normalized_goal = goal.strip()
        if not normalized_goal:
            raise ValueError("El objetivo no puede estar vacio.")
        session = ComputerUseSession(goal=normalized_goal)
        self.session_store.save(session)
        return session

    async def run_goal(self, goal: str, *, max_iterations: int | None = None) -> ComputerUseSession:
        return await self.run_session(self.create_session(goal).id, max_iterations=max_iterations)

    async def run_session(
        self,
        session_id: str,
        *,
        max_iterations: int | None = None,
        confirmation_tokens: dict[str, str] | None = None,
    ) -> ComputerUseSession:
        session = self.session_store.get(session_id)
        if session is None:
            raise KeyError(f"Sesion de Computer Use no encontrada: {session_id}")
        if session.status not in {ComputerUseStatus.CREATED, ComputerUseStatus.WAITING_CONFIRMATION}:
            raise ValueError(f"La sesion no se puede ejecutar desde estado {session.status.value}.")
        session.transition(ComputerUseStatus.RUNNING)
        self._cancel_events[session.id] = asyncio.Event()
        self._tasks[session.id] = asyncio.current_task()
        self.session_store.save(session)
        await self._publish(EventType.COMPUTER_USE_STARTED, {"session_id": session.id, "goal": session.goal})
        limit = self.max_iterations if max_iterations is None else max_iterations
        if limit < 1:
            raise ValueError("max_iterations debe ser mayor que cero.")
        try:
            for iteration in range(limit):
                if self._cancel_events[session.id].is_set():
                    session.transition(ComputerUseStatus.CANCELLED, error="cancelled")
                    await self._publish(EventType.COMPUTER_USE_CANCELLED, {
                        "session_id": session.id,
                        "error": session.error,
                    }, priority=EventPriority.HIGH)
                    break
                observation = self.observer.observe_desktop(include_ocr=False)
                session.record_observation(observation)
                self.session_store.save(session)
                changes = self.state_manager.update_observation(observation)
                await self._publish(EventType.COMPUTER_USE_OBSERVED, {
                    "session_id": session.id,
                    "iteration": iteration,
                    "changes": changes,
                    "summary": observation.screen_summary,
                })

                plan = self.planner.create_plan(session.goal, observation)
                graph = self.planner.execution_graph(plan)
                session.plan = {
                    "id": plan.id,
                    "goal": plan.goal,
                    "rationale": plan.rationale,
                    "steps": [
                        {
                            "id": step.id,
                            "capability": step.capability,
                            "description": step.description,
                            "args": step.args,
                            "expected": step.expected,
                            "status": step.status.value,
                        }
                        for step in plan.steps
                    ],
                }
                session.state.update({
                    "plan": session.plan,
                    "graph": graph.metadata,
                    "iteration": iteration,
                    "max_iterations": limit,
                })
                await self._publish(EventType.COMPUTER_USE_PLANNED, {
                    "session_id": session.id,
                    "plan_id": plan.id,
                    "steps": [step.description for step in plan.steps],
                })

                execution = await self.executor.execute_plan(
                    plan,
                    session_id=session.id,
                    confirmation_tokens=confirmation_tokens,
                )
                session.record_action({"plan_id": plan.id, "execution": execution})
                self.session_store.save(session)
                await self._publish(EventType.COMPUTER_USE_EXECUTED, {
                    "session_id": session.id,
                    "plan_id": plan.id,
                    "ok": execution["ok"],
                })

                refreshed = self.observer.observe_desktop(include_ocr=False)
                verification = self.verifier.verify_goal(session.goal, refreshed)
                session.record_verification(verification)
                await self._publish(EventType.COMPUTER_USE_VERIFIED, {
                    "session_id": session.id,
                    "ok": verification["ok"],
                    "reason": verification["reason"],
                })

                if execution["ok"] and verification["ok"]:
                    session.transition(ComputerUseStatus.COMPLETED)
                    await self._publish(EventType.COMPUTER_USE_COMPLETED, {"session_id": session.id})
                    break
                if execution["results"] and execution["results"][-1].get("policy", {}).get("requires_confirmation"):
                    session.transition(ComputerUseStatus.WAITING_CONFIRMATION)
                    session.error = "computer_use_confirmation_required"
                    policy = execution["results"][-1]["policy"]
                    session.state["pending_confirmation"] = {
                        "capability": policy.get("capability"),
                        "arguments": next(
                            (step.args for step in plan.steps if step.capability == policy.get("capability")),
                            {},
                        ),
                        "description": next(
                            (step.description for step in plan.steps if step.capability == policy.get("capability")),
                            "Accion sensible de Computer Use.",
                        ),
                        "reason": policy.get("reason"),
                        "risk_level": "high",
                        "source": "engine",
                    }
                    await self._publish(EventType.COMPUTER_USE_CONFIRMATION_REQUIRED, {
                        "session_id": session.id,
                        "capability": policy.get("capability"),
                    }, priority=EventPriority.HIGH)
                    break
            else:
                session.transition(ComputerUseStatus.ABORTED, error="iteration_limit_exceeded")
                await self._publish(EventType.COMPUTER_USE_FAILED, {
                    "session_id": session.id,
                    "error": session.error,
                }, priority=EventPriority.HIGH)
        except Exception as error:
            if session.status not in TERMINAL_STATUSES:
                session.transition(ComputerUseStatus.FAILED, error=self._safe_error(error))
            await self._publish(EventType.COMPUTER_USE_FAILED, {
                "session_id": session.id,
                "error": session.error,
            }, priority=EventPriority.HIGH)
        finally:
            self.session_store.save(session)
            self._cancel_events.pop(session.id, None)
            self._tasks.pop(session.id, None)
        return session

    async def observe(self, *, include_ocr: bool = False):
        observation = self.observer.observe_desktop(include_ocr=include_ocr)
        self.state_manager.update_observation(observation)
        return observation

    def cancel(self, session_id: str) -> bool:
        cancel_event = self._cancel_events.get(session_id)
        if cancel_event is not None:
            cancel_event.set()
            self.runtime.workflow_runner.engine.cancel()
            self.confirmations.revoke_session(session_id)
            return True
        session = self.session_store.get(session_id)
        if session is None or session.status in TERMINAL_STATUSES:
            return False
        if session.status in {ComputerUseStatus.CREATED, ComputerUseStatus.WAITING_CONFIRMATION}:
            session.transition(ComputerUseStatus.CANCELLED, error="cancelled")
            self.session_store.save(session)
            self.confirmations.revoke_session(session_id)
            self._publish_background(EventType.COMPUTER_USE_CANCELLED, {"session_id": session_id})
            return True
        return False

    def confirm(self, session_id: str, capability: str) -> str:
        session = self.session_store.get(session_id)
        if session is None or session.status not in {
            ComputerUseStatus.CREATED,
            ComputerUseStatus.WAITING_CONFIRMATION,
        }:
            raise ValueError("La sesion no admite confirmaciones.")
        return self.confirmations.issue(session_id, capability).token

    def _publish_background(self, event_type: EventType, payload: dict) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._publish(event_type, payload, priority=EventPriority.HIGH))

    async def _publish(self, event_type: EventType, payload: dict, *, priority: EventPriority = EventPriority.NORMAL) -> None:
        event_bus: EventBus = self.runtime.event_bus
        await event_bus.publish(OSEvent(event_type, payload, priority=priority, source="computer_use"))

    @staticmethod
    def _safe_error(error: Exception) -> str:
        if isinstance(error, (PermissionError, ValueError, KeyError)):
            return str(error)[:500]
        return "computer_use_internal_error"
