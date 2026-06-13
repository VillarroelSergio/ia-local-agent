from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ComputerUseRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1, max_length=1000)
    max_iterations: int = Field(default=3, ge=1, le=10)


class ComputerUseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1, max_length=1000)


class ComputerUseObserveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include_ocr: bool = False


class ComputerUseObserveWindowRequest(ComputerUseObserveRequest):
    window_handle: int | None = Field(default=None, ge=1)


class ComputerUseFindControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=200)
    window_handle: int | None = Field(default=None, ge=1)


class ComputerUseCapabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capability: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    approved: bool = False


class ComputerUseConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool


class ComputerUseSessionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    goal: str
    status: str
    state: dict[str, Any]
    observations: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    verifications: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    policy_decisions: list[dict[str, Any]] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    active_window: dict[str, Any] | None = None
    current_step_index: int = 0
    correlation_id: str
    created_at: str
    updated_at: str
    completed_at: str | None = None
    cancelled_at: str | None = None
    error: str | None = None


class ComputerUseSessionsResponse(BaseModel):
    sessions: list[ComputerUseSessionResponse]


class ComputerUseCancelResponse(BaseModel):
    cancelled: bool
    session_id: str


class ComputerUseConfirmationResponse(BaseModel):
    approved: bool
    session_id: str
    session: ComputerUseSessionResponse | None = None
