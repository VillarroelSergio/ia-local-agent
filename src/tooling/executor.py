"""Motor centralizado de ejecucion de tools."""

from __future__ import annotations

import asyncio
import inspect
from time import monotonic
from typing import Any

from pydantic import ValidationError

from .audit import JsonlAuditLog
from .models import (
    PermissionMode,
    ToolCall,
    ToolContext,
    ToolError,
    ToolResult,
)
from .permissions import ToolPermissionPolicy
from .registry import ToolRegistry


class ToolExecutor:
    """Valida, autoriza, ejecuta y audita tool calls."""

    def __init__(
        self,
        registry: ToolRegistry,
        permissions: ToolPermissionPolicy | None = None,
        audit_log: JsonlAuditLog | None = None,
    ):
        self.registry = registry
        self.permissions = permissions or ToolPermissionPolicy()
        self.audit_log = audit_log or JsonlAuditLog()

    def execute_sync(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        context: ToolContext | None = None,
        *,
        require_preapproved: bool = False,
    ) -> Any:
        """Compatibilidad sencilla para el agente actual."""
        call = ToolCall(name=name, arguments=arguments or {})
        result = asyncio.run(self.execute(
            call,
            context or ToolContext(),
            require_preapproved=require_preapproved,
        ))
        return result.to_message_content()

    async def execute(
        self,
        call: ToolCall,
        context: ToolContext | None = None,
        *,
        require_preapproved: bool = False,
    ) -> ToolResult:
        context = context or ToolContext()
        started_at = monotonic()
        definition = self.registry.get(call.name)

        if definition is None:
            return self._error(
                call,
                "tool_not_found",
                f"Tool no encontrada. Disponibles: {', '.join(self.registry.names())}",
                started_at,
            )

        try:
            parsed_arguments = definition.input_schema.model_validate(call.arguments)
        except ValidationError as error:
            return self._error(
                call,
                "validation_error",
                "Argumentos invalidos para la tool.",
                started_at,
                details=error.errors(),
                risk_level=definition.metadata.risk_level,
            )

        decision = self.permissions.evaluate(definition, parsed_arguments, context)

        if decision.mode == PermissionMode.DENY:
            return self._error(
                call,
                "permission_denied",
                decision.reason,
                started_at,
                risk_level=definition.metadata.risk_level,
            )

        if decision.mode == PermissionMode.CONFIRM and not require_preapproved:
            return ToolResult(
                call_id=call.id,
                tool_name=definition.name,
                ok=False,
                requires_user_action=True,
                risk_level=definition.metadata.risk_level,
                duration_ms=self._duration_ms(started_at),
                error=ToolError(
                    type="confirmation_required",
                    message=decision.reason,
                    details={"arguments": parsed_arguments.model_dump()},
                ),
            )

        self.audit_log.record(
            "tool.started",
            call_id=call.id,
            tool=definition.name,
            arguments=parsed_arguments.model_dump(),
            risk_level=definition.metadata.risk_level.value,
        )

        try:
            result = await asyncio.wait_for(
                self._invoke(definition.handler, parsed_arguments, context),
                timeout=definition.metadata.timeout_seconds,
            )
        except TimeoutError:
            return self._error(
                call,
                "timeout",
                f"La tool supero {definition.metadata.timeout_seconds} segundos.",
                started_at,
                risk_level=definition.metadata.risk_level,
            )
        except Exception as error:
            return self._error(
                call,
                "execution_error",
                "La tool fallo durante la ejecucion.",
                started_at,
                details=str(error),
                risk_level=definition.metadata.risk_level,
            )

        duration_ms = self._duration_ms(started_at)
        self.audit_log.record(
            "tool.finished",
            call_id=call.id,
            tool=definition.name,
            ok=True,
            duration_ms=duration_ms,
        )
        return ToolResult(
            call_id=call.id,
            tool_name=definition.name,
            ok=True,
            result=result,
            duration_ms=duration_ms,
            risk_level=definition.metadata.risk_level,
        )

    async def _invoke(self, handler, parsed_arguments, context):
        value = handler(parsed_arguments, context)

        if inspect.isawaitable(value):
            return await value

        return value

    def _error(
        self,
        call: ToolCall,
        error_type: str,
        message: str,
        started_at: float,
        *,
        details: Any | None = None,
        risk_level=None,
    ) -> ToolResult:
        duration_ms = self._duration_ms(started_at)
        self.audit_log.record(
            "tool.failed",
            call_id=call.id,
            tool=call.name,
            error_type=error_type,
            message=message,
            duration_ms=duration_ms,
        )
        return ToolResult(
            call_id=call.id,
            tool_name=call.name,
            ok=False,
            error=ToolError(type=error_type, message=message, details=details),
            duration_ms=duration_ms,
            risk_level=risk_level,
        )

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return int((monotonic() - started_at) * 1000)
