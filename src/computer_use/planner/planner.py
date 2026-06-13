"""Goal-to-plan conversion for Computer Use."""

from __future__ import annotations

try:
    from computer_use.models import DesktopObservation, ExecutionGraph, Plan, PlanStep
except ModuleNotFoundError:
    from src.computer_use.models import DesktopObservation, ExecutionGraph, Plan, PlanStep


class ComputerUsePlanner:
    """Conservative planner that emits semantic capabilities.

    This is intentionally deterministic for the first runtime layer. LLM-based
    planning can later produce the same Plan/PlanStep contracts.
    """

    def create_plan(self, goal: str, observation: DesktopObservation | None = None) -> Plan:
        normalized = goal.lower()
        steps: list[PlanStep] = []
        if any(token in normalized for token in ("observa", "observe", "ver pantalla", "estado")):
            steps.append(PlanStep("summarize_active_window", "Observar y resumir la ventana activa."))
        elif any(token in normalized for token in ("texto", "leer", "extract")):
            steps.append(PlanStep("extract_visible_text", "Extraer texto visible de la ventana activa."))
        elif any(token in normalized for token in ("enfoca", "focus", "abre ventana")):
            steps.append(PlanStep("focus_window", "Enfocar la ventana solicitada.", args={"query": goal}))
        else:
            steps.extend((
                PlanStep("summarize_active_window", "Observar el estado actual antes de actuar."),
                PlanStep("run_safe_workflow", "Ejecutar el objetivo mediante workflow semantico.", args={"goal": goal}),
            ))
        return Plan(
            goal=goal,
            steps=tuple(steps),
            rationale="Plan determinista inicial basado en capacidades semanticas.",
        )

    def execution_graph(self, plan: Plan) -> ExecutionGraph:
        nodes = tuple(step.id for step in plan.steps)
        edges = tuple((nodes[index], nodes[index + 1]) for index in range(len(nodes) - 1))
        return ExecutionGraph(plan_id=plan.id, nodes=nodes, edges=edges)

    def next_step(self, plan: Plan) -> PlanStep | None:
        for step in plan.steps:
            if step.status.value == "pending":
                return step
        return None
