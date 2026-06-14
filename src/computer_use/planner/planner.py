"""Goal-to-plan conversion for Computer Use."""

from __future__ import annotations

import re

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
        quoted_text = self._quoted_text(goal)
        mentions_notepad = any(token in normalized for token in ("notepad", "bloc de notas"))
        wants_open = any(token in normalized for token in ("abre", "abrir", "inicia", "arranca"))
        wants_observe = any(token in normalized for token in ("analiza", "observa", "resume", "controles accesibles"))
        wants_write = quoted_text is not None and any(token in normalized for token in ("escribe", "introduce"))
        wants_save = any(token in normalized for token in ("pulsa guardar", "guarda el documento", "guardar"))

        if mentions_notepad and wants_open:
            steps.append(PlanStep(
                "open_application",
                "Abrir una instancia de Notepad.",
                args={"app_name": "notepad"},
                expected={"window_process": "notepad"},
            ))
        if wants_write:
            steps.append(PlanStep(
                "fill_text_field",
                "Escribir en el documento activo de Notepad.",
                args={"name": "documento", "text": quoted_text},
                expected={"text_contains": quoted_text},
            ))
        if wants_save:
            steps.append(PlanStep(
                "click_ui_control",
                "Invocar el control Guardar.",
                args={"name": "Guardar"},
                expected={"control_invoked": "Guardar"},
            ))
        if wants_observe:
            steps.append(PlanStep("summarize_active_window", "Observar y resumir la ventana activa."))
        elif not steps and any(token in normalized for token in ("observa", "observe", "ver pantalla", "estado")):
            steps.append(PlanStep("summarize_active_window", "Observar y resumir la ventana activa."))
        elif not steps and any(token in normalized for token in ("texto", "leer", "extract")):
            steps.append(PlanStep("extract_visible_text", "Extraer texto visible de la ventana activa."))
        elif not steps and any(token in normalized for token in ("enfoca", "focus", "abre ventana")):
            steps.append(PlanStep("focus_window", "Enfocar la ventana solicitada.", args={"query": goal}))
        elif not steps:
            steps.extend((
                PlanStep("summarize_active_window", "Observar el estado actual antes de actuar."),
                PlanStep("run_safe_workflow", "Ejecutar el objetivo mediante workflow semantico.", args={"goal": goal}),
            ))
        return Plan(
            goal=goal,
            steps=tuple(steps),
            rationale="Plan determinista inicial basado en capacidades semanticas.",
        )

    @staticmethod
    def _quoted_text(goal: str) -> str | None:
        match = re.search(r"[\"'](?P<text>.+?)[\"']", goal)
        return match.group("text").strip() if match else None

    def execution_graph(self, plan: Plan) -> ExecutionGraph:
        nodes = tuple(step.id for step in plan.steps)
        edges = tuple((nodes[index], nodes[index + 1]) for index in range(len(nodes) - 1))
        return ExecutionGraph(plan_id=plan.id, nodes=nodes, edges=edges)

    def next_step(self, plan: Plan) -> PlanStep | None:
        for step in plan.steps:
            if step.status.value == "pending":
                return step
        return None
