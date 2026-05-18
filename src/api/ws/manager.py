from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self, max_message_bytes: int = 64_000):
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self.max_message_bytes = max_message_bytes

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        self.rooms[room].add(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        self.rooms[room].discard(websocket)

    async def send_json(self, websocket: WebSocket, payload: dict):
        await asyncio.wait_for(websocket.send_json(payload), timeout=5)

    async def broadcast(self, room: str, payload: dict):
        stale = []
        for websocket in self.rooms.get(room, set()):
            try:
                await self.send_json(websocket, payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket, room)


manager = ConnectionManager()
