"""Async event bus for OS integration."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any
from uuid import uuid4


class EventType(str, Enum):
    WINDOW_FOCUS_CHANGED = "window.focus_changed"
    WINDOW_STATE_CHANGED = "window.state_changed"
    SESSION_LOCKED = "session.locked"
    SESSION_UNLOCKED = "session.unlocked"
    SYSTEM_SUSPEND = "system.suspend"
    SYSTEM_RESUME = "system.resume"
    BATTERY_CHANGED = "battery.changed"
    NETWORK_CHANGED = "network.changed"
    DEVICE_CHANGED = "device.changed"
    CLIPBOARD_CHANGED = "clipboard.changed"
    AUDIO_DEVICE_CHANGED = "audio.device_changed"
    PROCESS_STARTED = "process.started"
    PROCESS_STOPPED = "process.stopped"
    MONITOR_CHANGED = "monitor.changed"
    IDLE_THRESHOLD_REACHED = "idle.threshold_reached"
    HOTKEY_PRESSED = "hotkey.pressed"
    AUTOMATION_STARTED = "automation.started"
    AUTOMATION_FINISHED = "automation.finished"
    ERROR = "runtime.error"


class EventPriority(IntEnum):
    LOW = 10
    NORMAL = 50
    HIGH = 90


@dataclass(frozen=True)
class OSEvent:
    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    id: str = field(default_factory=lambda: f"event_{uuid4().hex}")
    created_at: datetime = field(default_factory=datetime.now)
    source: str = "os_integration"


EventHandler = Callable[[OSEvent], Awaitable[None] | None]
EventMiddleware = Callable[[OSEvent], Awaitable[OSEvent | None] | OSEvent | None]


class EventBus:
    """Priority-aware async queue with bounded backpressure."""

    def __init__(self, *, max_queue_size: int = 1000):
        self._queue: asyncio.PriorityQueue[tuple[int, int, OSEvent]] = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._subscribers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._wildcard_subscribers: list[EventHandler] = []
        self._middleware: list[EventMiddleware] = []
        self._task: asyncio.Task | None = None
        self._closed = asyncio.Event()
        self._sequence = 0
        self.dropped_events = 0

    def subscribe(self, event_type: EventType | None, handler: EventHandler) -> None:
        if event_type is None:
            self._wildcard_subscribers.append(handler)
            return
        self._subscribers[event_type].append(handler)

    def add_middleware(self, middleware: EventMiddleware) -> None:
        self._middleware.append(middleware)

    async def publish(self, event: OSEvent) -> bool:
        processed = event
        for middleware in self._middleware:
            value = middleware(processed)
            processed = await value if asyncio.iscoroutine(value) else value
            if processed is None:
                return False

        self._sequence += 1
        item = (-int(processed.priority), self._sequence, processed)
        try:
            self._queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            self.dropped_events += 1
            return False

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._closed.clear()
            self._task = asyncio.create_task(self._run(), name="os-event-bus")

    async def stop(self) -> None:
        self._closed.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while not self._closed.is_set():
            _, _, event = await self._queue.get()
            handlers = [*self._subscribers.get(event.event_type, []), *self._wildcard_subscribers]
            for handler in handlers:
                try:
                    result = handler(event)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    # Subscribers are isolated so one faulty reaction does not
                    # stop the bus. Audit/logging can be attached as middleware.
                    continue
