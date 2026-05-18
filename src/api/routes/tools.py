from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.dependencies import tool_service
from src.api.schemas.tools import ToolConfirmationRequest, ToolExecuteRequest

router = APIRouter()


@router.get("/tools")
async def list_tools():
    return tool_service().list_tools()


@router.get("/tools/audit")
async def audit(limit: int = 100):
    return tool_service().audit(limit=limit)


@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    tool = tool_service().get_tool(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool no encontrada.")
    return tool


@router.post("/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, request: ToolExecuteRequest):
    return await tool_service().execute(
        tool_name,
        request.arguments,
        conversation_id=request.conversation_id,
        preapproved=request.preapproved,
    )


@router.post("/tools/confirm")
async def confirm_tool(request: ToolConfirmationRequest):
    if not request.approved:
        return {"ok": False, "cancelled": True}
    return await tool_service().execute(
        request.tool_name,
        request.arguments,
        conversation_id=request.conversation_id,
        preapproved=True,
    )
