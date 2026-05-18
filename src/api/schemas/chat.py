from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    id: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=20000)
    conversation_id: str | None = None
    provider: str | None = None
    model: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = False
    use_tools: bool = True
    correlation_id: str | None = None


class ToolCallEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: str | None = None
    status: str = "requested"


class AgentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    duration_ms: int
    approximate_tokens: int = 0
    tools_executed: list[str] = Field(default_factory=list)
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    correlation_id: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    message: ChatMessage
    tool_calls: list[ToolCallEvent] = Field(default_factory=list)
    metadata: AgentMetadata


class StreamingChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    delta: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    request_id: str
    correlation_id: str | None = None
