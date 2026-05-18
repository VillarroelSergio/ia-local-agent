from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.dependencies import api_settings, event_bus
from src.api.ws.manager import manager

router = APIRouter()


def authorized(websocket: WebSocket) -> bool:
    token = websocket.query_params.get("token") or websocket.headers.get("x-api-key")
    return token == api_settings().api_key


@router.websocket("/ws/events")
async def events_ws(websocket: WebSocket):
    if not authorized(websocket):
        await websocket.close(code=1008)
        return
    room = "events"
    await manager.connect(websocket, room)
    heartbeat = 0
    try:
        async for event in event_bus().subscribe():
            heartbeat += 1
            await manager.send_json(websocket, event.model_dump())
            if heartbeat % 20 == 0:
                await manager.send_json(websocket, {"type": "heartbeat"})
            await asyncio.sleep(0)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
