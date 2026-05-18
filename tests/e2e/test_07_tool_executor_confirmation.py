import asyncio
import json

from src.tooling import ToolCall, ToolContext, ToolExecutor
from src.tooling.audit import JsonlAuditLog
from src.tooling.permissions import ToolPermissionPolicy
from src.tools import build_tool_registry


def test_tool_executor_confirmation_and_audit(tmp_path, test_settings):
    registry = build_tool_registry()
    audit_path = tmp_path / "audit.jsonl"
    executor = ToolExecutor(
        registry=registry,
        permissions=ToolPermissionPolicy(
            tools_require_confirmation=True,
            allowed_roots=test_settings.tool_allowed_roots,
            confirm_roots=test_settings.tool_confirm_read_roots,
        ),
        audit_log=JsonlAuditLog(audit_path),
    )

    system_result = asyncio.run(executor.execute(
        ToolCall(name="get_system_info"),
        ToolContext(settings=test_settings),
        require_preapproved=True,
    ))
    assert system_result.ok
    assert "system" in system_result.result

    blocked_result = asyncio.run(executor.execute(
        ToolCall(name="run_powershell", arguments={"command": "Get-Date"}),
        ToolContext(settings=test_settings),
        require_preapproved=False,
    ))
    assert not blocked_result.ok
    assert blocked_result.requires_user_action
    assert blocked_result.error.type == "confirmation_required"

    events = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert any(event["event_type"] == "tool.started" for event in events)
    assert any(event["event_type"] == "tool.finished" for event in events)
