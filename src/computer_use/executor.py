"""Computer Use executor backed by WorkflowRunner."""

from __future__ import annotations

import asyncio
from dataclasses import asdict

try:
    from computer_use.capabilities import ConfirmationStore, require_capability
    from computer_use.models import Plan, PlanStep
    from computer_use.observer.uia import UIAutomationService
    from os_integration.automation import WorkflowRunner
    from os_integration.apps import ApplicationManager
    from os_integration.models import AutomationStep, AutomationWorkflow
    from os_integration.security import OSScope, OSSecurityPolicy
except ModuleNotFoundError:
    from src.computer_use.capabilities import ConfirmationStore, require_capability
    from src.computer_use.models import Plan, PlanStep
    from src.computer_use.observer.uia import UIAutomationService
    from src.os_integration.automation import WorkflowRunner
    from src.os_integration.apps import ApplicationManager
    from src.os_integration.models import AutomationStep, AutomationWorkflow
    from src.os_integration.security import OSScope, OSSecurityPolicy


class ComputerUseExecutor:
    def __init__(
        self,
        workflow_runner: WorkflowRunner,
        *,
        security: OSSecurityPolicy | None = None,
        confirmations: ConfirmationStore | None = None,
        ui_automation: UIAutomationService | None = None,
        application_manager: ApplicationManager | None = None,
    ):
        self.workflow_runner = workflow_runner
        self.security = security or workflow_runner.engine.security
        self.confirmations = confirmations or ConfirmationStore()
        self.ui_automation = ui_automation or UIAutomationService()
        self.application_manager = application_manager or ApplicationManager()

    async def execute_plan(self, plan: Plan, *, session_id: str, confirmation_tokens: dict[str, str] | None = None) -> dict:
        results = []
        for step in plan.steps:
            results.append(await self.execute_step(
                step,
                session_id=session_id,
                confirmation_token=(
                    (confirmation_tokens or {}).get(step.id)
                    or (confirmation_tokens or {}).get(step.capability)
                ),
            ))
            if not results[-1]["ok"]:
                break
        return {"ok": all(result["ok"] for result in results), "results": results}

    async def execute_step(
        self,
        step: PlanStep,
        *,
        session_id: str = "standalone",
        confirmation_token: str | None = None,
    ) -> dict:
        decision = self._evaluate_capability(step, session_id=session_id, confirmation_token=confirmation_token)
        if not decision["allowed"]:
            return {"ok": False, "step_id": step.id, "error": decision["reason"], "policy": decision}
        if step.capability in {"click_ui_control", "fill_text_field"}:
            return self._execute_uia_step(step, decision)
        if step.capability == "open_application":
            return await self._open_application(step, decision)
        workflow = self._workflow_for_step(step)
        if workflow is None:
            return {
                "ok": step.capability in {
                    "observe_desktop", "observe_active_window", "summarize_active_window",
                    "extract_visible_text", "find_ui_control",
                },
                "step_id": step.id,
                "result": {"delegated_to_observer": True},
                "policy": decision,
            }
        results = await self.workflow_runner.run(workflow)
        return {
            "ok": all(result.ok for result in results),
            "step_id": step.id,
            "workflow_id": workflow.id,
            "results": [asdict(result) for result in results],
            "policy": decision,
        }

    async def _open_application(self, step: PlanStep, decision: dict) -> dict:
        app_name = str(step.args.get("app_name") or "").strip()
        if not app_name:
            return {"ok": False, "step_id": step.id, "error": "Falta app_name.", "policy": decision}
        before = {
            (window.handle, window.pid)
            for window in self.workflow_runner.engine.window_manager.list_windows(limit=300)
        }
        launch = self.application_manager.launch(app_name)
        if not launch.opened:
            return {"ok": False, "step_id": step.id, "error": launch.error, "policy": decision}
        for _ in range(20):
            await asyncio.sleep(0.1)
            candidates = [
                window
                for window in self.workflow_runner.engine.window_manager.find_windows(app_name, limit=10)
                if (window.handle, window.pid) not in before
            ]
            if len(candidates) == 1:
                window = candidates[0]
                return {
                    "ok": True,
                    "step_id": step.id,
                    "result": {
                        "opened": True,
                        "window": {
                            "handle": window.handle,
                            "pid": window.pid,
                            "title": window.title,
                            "process_name": window.process_name,
                        },
                    },
                    "policy": decision,
                }
            if len(candidates) > 1:
                return {
                    "ok": False,
                    "step_id": step.id,
                    "error": "La apertura creo varias ventanas y no puede identificarse una de forma segura.",
                    "policy": decision,
                }
        return {
            "ok": False,
            "step_id": step.id,
            "error": "La aplicacion se inicio, pero no se encontro una ventana nueva verificable.",
            "policy": decision,
        }

    def _evaluate_capability(self, step: PlanStep, *, session_id: str, confirmation_token: str | None) -> dict:
        capability = require_capability(step.capability)
        active = self.workflow_runner.engine.window_manager.get_active_window()
        scope = {
            "focus_window": OSScope.WINDOW_CONTROL,
            "organize_windows": OSScope.WINDOW_CONTROL,
            "click_ui_control": OSScope.MOUSE_INPUT,
            "fill_text_field": OSScope.KEYBOARD_INPUT,
        }.get(step.capability, OSScope.WINDOW_INSPECT)
        decision = self.security.evaluate_scope(scope, active)
        if not decision.allowed:
            return {"allowed": False, "reason": decision.reason, "requires_confirmation": decision.requires_confirmation}
        requires_confirmation = decision.requires_confirmation or capability.requires_confirmation
        if requires_confirmation and not self.confirmations.consume(
            confirmation_token,
            session_id=session_id,
            capability=step.capability,
        ):
            return {
                "allowed": False,
                "reason": "computer_use_confirmation_required",
                "requires_confirmation": True,
                "capability": step.capability,
            }
        return {
            "allowed": True,
            "reason": decision.reason,
            "requires_confirmation": requires_confirmation,
            "capability": step.capability,
        }

    def _execute_uia_step(self, step: PlanStep, decision: dict) -> dict:
        query = str(step.args.get("query") or step.args.get("name") or "").strip()
        handle = step.args.get("window_handle")
        try:
            if step.capability == "click_ui_control":
                action = self.ui_automation.invoke_named_control(query, window_handle=handle)
            else:
                controls = self.ui_automation.find_inputs(window_handle=handle, query=query)
                if not controls:
                    raise ValueError("Control UIA no encontrado.")
                action = self.ui_automation.set_text(controls[0], str(step.args.get("text") or ""))
            return {"ok": bool(action.get("ok")), "step_id": step.id, "result": action, "policy": decision}
        except (PermissionError, RuntimeError, ValueError) as error:
            return {"ok": False, "step_id": step.id, "error": str(error), "policy": decision}

    def _workflow_for_step(self, step: PlanStep) -> AutomationWorkflow | None:
        if step.capability == "focus_window":
            return AutomationWorkflow(
                name="computer_use_focus_window",
                steps=(AutomationStep(
                    action="focus_window",
                    args=step.args,
                    require_confirmation=False,
                    retry_count=1,
                ),),
                metadata={"computer_use_step_id": step.id, "capability": step.capability},
            )
        if step.capability == "run_safe_workflow":
            return AutomationWorkflow(
                name="computer_use_semantic_wait",
                steps=(AutomationStep(action="wait", args={"seconds": 0.1}, require_confirmation=False),),
                metadata={
                    "computer_use_step_id": step.id,
                    "capability": step.capability,
                    "note": "Placeholder seguro: requiere planner especifico para acciones reales.",
                },
            )
        return None
