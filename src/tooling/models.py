"""Modelos base para registry, permisos y ejecucion de tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    """Nivel de riesgo operativo de una tool."""

    SAFE = "safe"
    READ_ONLY = "read_only"
    USER_CONFIRM = "user_confirm"
    DESTRUCTIVE = "destructive"
    ADMIN = "admin"


class PermissionMode(str, Enum):
    """Resultado de una evaluacion de permisos."""

    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


class ToolMetadata(BaseModel):
    """Metadatos indexables y auditables de una tool."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    category: str = "general"
    version: str = "1.0.0"
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    risk_level: RiskLevel = RiskLevel.USER_CONFIRM
    requires_confirmation: bool = True
    timeout_seconds: int = Field(default=15, ge=1, le=120)
    enabled: bool = True


class ToolContext(BaseModel):
    """Contexto de ejecucion que acompana una tool call."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    conversation_id: str | None = None
    user_id: str | None = None
    working_directory: str | None = None
    settings: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """Tool call normalizada, venga de OpenAI-compatible, CLI o workflow."""

    id: str = Field(default_factory=lambda: f"call_{uuid4().hex}")
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None
    user_id: str | None = None


class ToolError(BaseModel):
    """Error normalizado para que el agente pueda recuperarse."""

    type: str
    message: str
    details: Any | None = None


class ToolResult(BaseModel):
    """Resultado estable para UI, auditoria y mensajes tool del provider."""

    call_id: str
    tool_name: str
    ok: bool
    result: Any | None = None
    error: ToolError | None = None
    duration_ms: int = 0
    requires_user_action: bool = False
    risk_level: RiskLevel | None = None
    trace: dict[str, Any] = Field(default_factory=dict)

    def to_message_content(self) -> Any:
        """Devuelve un payload compacto compatible con mensajes tool."""
        if self.ok:
            return self.result

        return {
            "error": self.error.message if self.error else "Tool failed",
            "error_type": self.error.type if self.error else "unknown_error",
            "details": self.error.details if self.error else None,
        }


class PermissionDecision(BaseModel):
    """Decision explicita del motor de permisos."""

    mode: PermissionMode
    reason: str
    risk_level: RiskLevel


ToolHandler = Callable[[BaseModel, ToolContext], Any | Awaitable[Any]]


class ToolDefinition(BaseModel):
    """Definicion completa de una tool registrable."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: ToolMetadata
    input_schema: type[BaseModel]
    output_schema: type[BaseModel] | None = None
    handler: ToolHandler

    @property
    def name(self) -> str:
        return self.metadata.name

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.metadata.name,
                "description": self.metadata.description,
                "parameters": self.input_schema.model_json_schema(),
            },
        }
