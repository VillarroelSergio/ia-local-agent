"""Desktop automation runtime primitives."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from .events import EventBus, EventType, OSEvent
from .models import AutomationStep, AutomationWorkflow
from .ocr import OCRService
from .screenshots import ScreenshotService
from .security import OSScope, OSSecurityPolicy
from .windows import WindowManager

try:
    import pyautogui
except ImportError:
    pyautogui = None


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 1
    delay_seconds: float = 0.2


@dataclass(frozen=True)
class StepResult:
    step_id: str
    ok: bool
    result: Any = None
    error: str | None = None


class AutomationEngine:
    """Executes bounded desktop actions under OS security policy."""

    def __init__(
        self,
        *,
        security: OSSecurityPolicy | None = None,
        window_manager: WindowManager | None = None,
        screenshot_service: ScreenshotService | None = None,
        ocr_service: OCRService | None = None,
    ):
        self.security = security or OSSecurityPolicy()
        self.window_manager = window_manager or WindowManager(security=self.security)
        self.screenshot_service = screenshot_service or ScreenshotService(security=self.security, window_manager=self.window_manager)
        self.ocr_service = ocr_service or OCRService(security=self.security, screenshot_service=self.screenshot_service)
        self._cancel_event = asyncio.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    async def execute_step(self, step: AutomationStep) -> StepResult:
        self._cancel_event.clear()
        for attempt in range(step.retry_count + 1):
            if self._cancel_event.is_set():
                return StepResult(step.id, False, error="cancelled")
            try:
                result = await asyncio.wait_for(self._execute_once(step), timeout=step.timeout_seconds)
                return StepResult(step.id, True, result=result)
            except Exception as error:
                if attempt >= step.retry_count:
                    return StepResult(step.id, False, error=str(error))
                await asyncio.sleep(0.2)
        return StepResult(step.id, False, error="retry_exhausted")

    async def _execute_once(self, step: AutomationStep) -> Any:
        active = self.window_manager.get_active_window()
        if step.action in {"click", "move", "type", "hotkey", "press"}:
            scope = OSScope.MOUSE_INPUT if step.action in {"click", "move"} else OSScope.KEYBOARD_INPUT
            decision = self.security.evaluate_scope(scope, active)
            if not decision.allowed:
                raise PermissionError(decision.reason)
            if decision.requires_confirmation and step.require_confirmation:
                raise PermissionError("automation_confirmation_required")
            if pyautogui is None:
                raise RuntimeError("pyautogui no esta instalado.")

        if step.action == "move":
            pyautogui.moveTo(step.args["x"], step.args["y"], duration=step.args.get("duration", 0.1))
            return {"moved": True}
        if step.action == "click":
            pyautogui.click(
                x=step.args.get("x"),
                y=step.args.get("y"),
                button=step.args.get("button", "left"),
                clicks=step.args.get("clicks", 1),
            )
            return {"clicked": True}
        if step.action == "type":
            pyautogui.write(step.args["text"], interval=step.args.get("interval", 0.02))
            return {"typed": len(step.args["text"])}
        if step.action == "hotkey":
            pyautogui.hotkey(*step.args["keys"])
            return {"hotkey": step.args["keys"]}
        if step.action == "press":
            pyautogui.press(step.args["key"])
            return {"pressed": step.args["key"]}
        if step.action == "wait":
            await asyncio.sleep(float(step.args.get("seconds", 1)))
            return {"waited": step.args.get("seconds", 1)}
        if step.action == "ocr_contains":
            result = self.ocr_service.read_screen()
            expected = step.args["text"].lower()
            return {"matched": expected in result.text.lower(), "text": result.text[:500]}
        raise ValueError(f"Accion de automatizacion no soportada: {step.action}")


class WorkflowExecutor:
    def __init__(self, engine: AutomationEngine, *, event_bus: EventBus | None = None):
        self.engine = engine
        self.event_bus = event_bus

    async def run(self, workflow: AutomationWorkflow) -> list[StepResult]:
        if self.event_bus:
            await self.event_bus.publish(OSEvent(EventType.AUTOMATION_STARTED, {"workflow": workflow.name, "id": workflow.id}))
        results: list[StepResult] = []
        for step in workflow.steps:
            result = await self.engine.execute_step(step)
            results.append(result)
            if not result.ok:
                break
        if self.event_bus:
            await self.event_bus.publish(OSEvent(EventType.AUTOMATION_FINISHED, {
                "workflow": workflow.name,
                "id": workflow.id,
                "ok": all(result.ok for result in results),
            }))
        return results
