from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class WorkflowRunInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow_name: str
    status: str
    progress: float = 0.0
    logs: list[dict[str, Any]] = Field(default_factory=list)
