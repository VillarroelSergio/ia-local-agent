"""Estado compartido para workflows agentic."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict


class WorkflowStatus(str, Enum):
    RUNNING = "running"
    NEEDS_CONFIRMATION = "needs_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentDecision(TypedDict, total=False):
    """Decision resumida y auditable del agente."""

    node: str
    decision: str
    reason_summary: str
    selected_tool: str
    expected_result: str
    risk: str


class AgentState(TypedDict, total=False):
    """Estado canonico para LangGraph y workflows manuales."""

    conversation_id: str
    user_input: str
    messages: list[dict[str, Any]]
    plan: list[dict[str, Any]]
    decisions: list[AgentDecision]
    selected_tools: list[str]
    retrieved_context: list[dict[str, Any]]
    memory_context: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    final_answer: str | None
    errors: list[dict[str, Any]]
    status: WorkflowStatus
    step_count: int
    max_steps: int
