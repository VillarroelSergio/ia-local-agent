from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.dependencies import agent_service, api_settings
from src.api.schemas.chat import ChatRequest
from src.api.ws.manager import manager

router = APIRouter()


def authorized(websocket: WebSocket) -> bool:
    token = websocket.query_params.get("token") or websocket.headers.get("x-api-key")
    return token == api_settings().api_key


@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    if not authorized(websocket):
        await websocket.close(code=1008)
        return
    room = websocket.query_params.get("conversation_id") or "chat"
    await manager.connect(websocket, room)
    try:
        while True:
            payload = await websocket.receive_json()
            kind = payload.get("type", "message")
            if kind == "ping":
                await manager.send_json(websocket, {"type": "pong"})
                continue
            if kind == "cancel":
                agent_service().cancel(payload.get("request_id", ""))
                await manager.send_json(websocket, {"type": "cancel.accepted", "request_id": payload.get("request_id")})
                continue
            if kind == "tool.confirm":
                await manager.send_json(websocket, {"type": "tool.confirm.received", "correlation_id": payload.get("correlation_id")})
                continue
            request = ChatRequest(
                message=payload["message"],
                conversation_id=payload.get("conversation_id"),
                model=payload.get("model"),
                provider=payload.get("provider"),
                context=payload.get("context") or {},
                stream=True,
                use_tools=payload.get("use_tools", True),
                correlation_id=payload.get("correlation_id"),
            )
            async for chunk in agent_service().stream_chat(request):
                await manager.send_json(websocket, chunk.model_dump())
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
