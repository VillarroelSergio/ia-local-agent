"""Computer Use executor backed by WorkflowRunner."""

from __future__ import annotations

from dataclasses import asdict

try:
    from computer_use.capabilities import ConfirmationStore, require_capability
    from computer_use.models import Plan, PlanStep
    from os_integration.automation import WorkflowRunner
    from os_integration.models import AutomationStep, AutomationWorkflow
    from os_integration.security import OSScope, OSSecurityPolicy
except ModuleNotFoundError:
    from src.computer_use.capabilities import ConfirmationStore, require_capability
    from src.computer_use.models import Plan, PlanStep
    from src.os_integration.automation import WorkflowRunner
    from src.os_integration.models import AutomationStep, AutomationWorkflow
    from src.os_integration.security import OSScope, OSSecurityPolicy


class ComputerUseExecutor:
    def __init__(
        self,
        workflow_runner: WorkflowRunner,
        *,
        security: OSSecurityPolicy | None = None,
        confirmations: ConfirmationStore | None = None,
    ):
        self.workflow_runner = workflow_runner
        self.security = security or workflow_runner.engine.security
        self.confirmations = confirmations or ConfirmationStore()

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

    def _evaluate_capability(self, step: PlanStep, *, session_id: str, confirmation_token: str | None) -> dict:
        capability = require_capability(step.capability)
        active = self.workflow_runner.engine.window_manager.get_active_window()
        scope = OSScope.WINDOW_CONTROL if step.capability in {"focus_window", "organize_windows"} else OSScope.WINDOW_INSPECT
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
