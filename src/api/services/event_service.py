from __future__ import annotations

import asyncio
from collections import deque
from typing import AsyncIterator

from src.api.schemas.events import EventEnvelope


class EventBus:
    """Small in-process event bus for the local UI and tests."""

    def __init__(self, history_size: int = 500):
        self._subscribers: set[asyncio.Queue[EventEnvelope]] = set()
        self._history: deque[EventEnvelope] = deque(maxlen=history_size)

    async def publish(self, event: EventEnvelope):
        self._history.append(event)
        stale = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                stale.append(queue)
        for queue in stale:
            self._subscribers.discard(queue)

    async def subscribe(self, max_queue: int = 100) -> AsyncIterator[EventEnvelope]:
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=max_queue)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)

    def history(self) -> list[EventEnvelope]:
        return list(self._history)
