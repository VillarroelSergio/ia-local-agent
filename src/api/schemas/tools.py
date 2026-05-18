from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    category: str
    risk_level: str
    requires_confirmation: bool
    schema_: dict[str, Any] = Field(alias="schema")


class ToolExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arguments: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None
    preapproved: bool = False
    correlation_id: str | None = None


class ToolExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call_id: str
    tool_name: str
    ok: bool
    result: Any | None = None
    error: dict[str, Any] | None = None
    requires_user_action: bool = False
    risk_level: str | None = None
    duration_ms: int = 0


class ToolConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    approved: bool
    conversation_id: str | None = None


class ToolAuditEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
