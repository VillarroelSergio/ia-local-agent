from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ComputerUseRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=1000)
    max_iterations: int = Field(default=3, ge=1, le=10)


class ComputerUseObserveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_ocr: bool = False


class ComputerUseSessionResponse(BaseModel):
    id: str
    goal: str
    status: str
    state: dict[str, Any]
    observations: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    created_at: str
    updated_at: str
    completed_at: str | None = None
    error: str | None = None


class ComputerUseSessionsResponse(BaseModel):
    sessions: list[ComputerUseSessionResponse]


class ComputerUseCancelResponse(BaseModel):
    cancelled: bool
    session_id: str
