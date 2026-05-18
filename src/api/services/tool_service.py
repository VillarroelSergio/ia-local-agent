from __future__ import annotations

import json
from pathlib import Path

from src.tooling import ToolCall, ToolContext
from src.tools import TOOL_EXECUTOR, TOOL_REGISTRY
from src.api.schemas.tools import ToolExecuteResponse, ToolInfo


class ToolService:
    def list_tools(self) -> list[ToolInfo]:
        return [self._info(definition) for definition in TOOL_REGISTRY.definitions()]

    def get_tool(self, name: str) -> ToolInfo | None:
        definition = TOOL_REGISTRY.get(name)
        return self._info(definition) if definition else None

    async def execute(self, name: str, arguments: dict, *, conversation_id=None, preapproved=False) -> ToolExecuteResponse:
        result = await TOOL_EXECUTOR.execute(
            ToolCall(name=name, arguments=arguments, conversation_id=conversation_id),
            ToolContext(conversation_id=conversation_id),
            require_preapproved=preapproved,
        )
        return ToolExecuteResponse(
            call_id=result.call_id,
            tool_name=result.tool_name,
            ok=result.ok,
            result=result.result,
            error=result.error.model_dump() if result.error else None,
            requires_user_action=result.requires_user_action,
            risk_level=result.risk_level.value if result.risk_level else None,
            duration_ms=result.duration_ms,
        )

    def audit(self, limit=100):
        path = Path("data/tool_audit.jsonl")
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]

    @staticmethod
    def _info(definition):
        metadata = definition.metadata
        return ToolInfo(
            name=definition.name,
            description=metadata.description,
            category=metadata.category,
            risk_level=metadata.risk_level.value,
            requires_confirmation=metadata.requires_confirmation,
            schema=definition.openai_schema(),
        )
