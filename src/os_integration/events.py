"""Async event bus for OS integration."""

from __future__ import annotations

import asyncio
import copy
import json
import time
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
    COMPUTER_USE_STARTED = "computer_use.started"
    COMPUTER_USE_OBSERVED = "computer_use.observed"
    COMPUTER_USE_PLANNED = "computer_use.planned"
    COMPUTER_USE_EXECUTED = "computer_use.executed"
    COMPUTER_USE_VERIFIED = "computer_use.verified"
    COMPUTER_USE_FAILED = "computer_use.failed"
    COMPUTER_USE_COMPLETED = "computer_use.completed"
    COMPUTER_USE_CANCELLED = "computer_use.cancelled"
    COMPUTER_USE_CONFIRMATION_REQUIRED = "computer_use.confirmation_required"
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
        processed = OSEvent(
            event_type=event.event_type,
            payload=_safe_payload(event.payload),
            priority=event.priority,
            id=event.id,
            created_at=event.created_at,
            source=str(event.source)[:100],
        )
        for middleware in self._middleware:
            try:
                value = middleware(processed)
                processed = await value if asyncio.iscoroutine(value) else value
            except Exception:
                return False
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


class DebounceMiddleware:
    def __init__(self, *, window_ms: int = 250):
        self.window_ms = window_ms
        self._last_seen: dict[tuple[EventType, str], float] = {}

    def __call__(self, event: OSEvent) -> OSEvent | None:
        key = (event.event_type, json.dumps(event.payload, sort_keys=True, default=str))
        now = time.monotonic()
        previous = self._last_seen.get(key)
        if previous is not None and (now - previous) * 1000 < self.window_ms:
            return None
        self._last_seen[key] = now
        return event


class ThrottleMiddleware:
    def __init__(self, *, max_events: int = 20, per_seconds: float = 1.0):
        self.max_events = max_events
        self.per_seconds = per_seconds
        self._timestamps: list[float] = []

    def __call__(self, event: OSEvent) -> OSEvent | None:
        now = time.monotonic()
        self._timestamps = [item for item in self._timestamps if now - item <= self.per_seconds]
        if len(self._timestamps) >= self.max_events:
            return None
        self._timestamps.append(now)
        return event


_SENSITIVE_KEYS = frozenset({
    "api_key", "authorization", "cookie", "password", "secret", "token",
    "access_token", "refresh_token", "private_key",
})


def _safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    def sanitize(value: Any, key: str = "") -> Any:
        if key.lower() in _SENSITIVE_KEYS:
            return "[redacted]"
        if isinstance(value, dict):
            return {str(item_key)[:200]: sanitize(item, str(item_key)) for item_key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [sanitize(item) for item in value]
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            return value.isoformat()
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        try:
            return copy.deepcopy(value)
        except Exception:
            return repr(value)[:500]

    sanitized = sanitize(payload)
    return sanitized if isinstance(sanitized, dict) else {}
