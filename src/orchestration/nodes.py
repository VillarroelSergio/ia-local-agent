"""Nodos reutilizables para graphs agentic."""

from __future__ import annotations

import json
from typing import Any

try:
    from tooling import ToolCall, ToolContext, ToolExecutor
except ModuleNotFoundError:
    from src.tooling import ToolCall, ToolContext, ToolExecutor

from .state import WorkflowStatus


def append_decision(state, *, node, decision, reason_summary, **extra):
    decisions = [*state.get("decisions", [])]
    decisions.append({
        "node": node,
        "decision": decision,
        "reason_summary": reason_summary,
        **extra,
    })
    return {"decisions": decisions}


def initialize_state(state):
    """Inicializa limites y contenedores del workflow."""
    return {
        "plan": state.get("plan", []),
        "decisions": state.get("decisions", []),
        "tool_calls": state.get("tool_calls", []),
        "tool_results": state.get("tool_results", []),
        "errors": state.get("errors", []),
        "step_count": state.get("step_count", 0),
        "max_steps": state.get("max_steps", 8),
        "status": WorkflowStatus.RUNNING,
    }


def plan_from_user_input(state):
    """Planner deterministic minimal; puede sustituirse por LLM planner."""
    user_input = state.get("user_input", "")
    plan = [{
        "step": "answer_or_select_tools",
        "description": "Responder con contexto disponible o pedir tools al modelo.",
    }]

    update = append_decision(
        state,
        node="planner",
        decision="created_minimal_plan",
        reason_summary="Se crea un plan inicial conservador para un turno de agente.",
    )
    update["plan"] = plan
    update["messages"] = [
        *state.get("messages", []),
        {"role": "user", "content": user_input},
    ]
    return update


async def execute_tool_calls(state, executor: ToolExecutor):
    """Ejecuta tool calls acumuladas en el estado."""
    results = [*state.get("tool_results", [])]
    errors = [*state.get("errors", [])]
    needs_confirmation = False

    for raw_call in state.get("tool_calls", []):
        function = raw_call.get("function", {})
        name = function.get("name") or raw_call.get("name")
        raw_arguments = function.get("arguments", raw_call.get("arguments", {}))

        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments or "{}")
            except json.JSONDecodeError as error:
                errors.append({
                    "type": "invalid_tool_arguments",
                    "tool": name,
                    "details": str(error),
                })
                continue
        else:
            arguments = raw_arguments or {}

        result = await executor.execute(
            ToolCall(id=raw_call.get("id", ""), name=name, arguments=arguments),
            ToolContext(conversation_id=state.get("conversation_id")),
        )
        result_payload = result.model_dump(mode="json")
        results.append(result_payload)

        if result.requires_user_action:
            needs_confirmation = True

    status = WorkflowStatus.NEEDS_CONFIRMATION if needs_confirmation else WorkflowStatus.RUNNING
    return {"tool_results": results, "errors": errors, "status": status}


def should_continue_after_tools(state) -> str:
    """Router simple para loops con limite."""
    if state.get("status") == WorkflowStatus.NEEDS_CONFIRMATION:
        return "needs_confirmation"

    step_count = state.get("step_count", 0) + 1

    if step_count >= state.get("max_steps", 8):
        return "finish"

    if state.get("final_answer"):
        return "finish"

    return "agent"


def finalize_with_summary(state):
    """Finalizador de fallback si un workflow termina sin respuesta LLM."""
    if state.get("final_answer"):
        return {"status": WorkflowStatus.COMPLETED}

    return {
        "status": WorkflowStatus.COMPLETED,
        "final_answer": "Workflow completado. Revisa tool_results para los resultados estructurados.",
    }
