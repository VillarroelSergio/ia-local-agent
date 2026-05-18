"""Global hotkey registration with optional keyboard backend."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from .events import EventBus, EventPriority, EventType, OSEvent
from .models import HotkeyBinding
from .security import OSScope, OSSecurityPolicy

try:
    import keyboard
except ImportError:
    keyboard = None


HotkeyCallback = Callable[[HotkeyBinding], None]


class HotkeyManager:
    def __init__(self, *, event_bus: EventBus | None = None, security: OSSecurityPolicy | None = None):
        self.event_bus = event_bus
        self.security = security or OSSecurityPolicy()
        self._bindings: dict[str, HotkeyBinding] = {}
        self._handles: dict[str, object] = {}
        self._callbacks: dict[str, HotkeyCallback] = {}

    def register(self, binding: HotkeyBinding, callback: HotkeyCallback | None = None) -> None:
        decision = self.security.evaluate_scope(OSScope.HOTKEY_REGISTER)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        if binding.name in self._bindings:
            self.unregister(binding.name)
        if keyboard is None:
            self._bindings[binding.name] = binding
            if callback:
                self._callbacks[binding.name] = callback
            return
        handle = keyboard.add_hotkey(binding.keys, lambda: self._emit(binding))
        self._bindings[binding.name] = binding
        self._handles[binding.name] = handle
        if callback:
            self._callbacks[binding.name] = callback

    def unregister(self, name: str) -> None:
        handle = self._handles.pop(name, None)
        if keyboard is not None and handle is not None:
            keyboard.remove_hotkey(handle)
        self._bindings.pop(name, None)
        self._callbacks.pop(name, None)

    def list_bindings(self) -> tuple[HotkeyBinding, ...]:
        return tuple(sorted(self._bindings.values(), key=lambda item: item.priority, reverse=True))

    def close(self) -> None:
        for name in list(self._bindings):
            self.unregister(name)

    def _emit(self, binding: HotkeyBinding) -> None:
        callback = self._callbacks.get(binding.name)
        if callback:
            callback(binding)
        if self.event_bus:
            event = OSEvent(
                EventType.HOTKEY_PRESSED,
                {"name": binding.name, "keys": binding.keys, "action": binding.action},
                priority=EventPriority.HIGH,
            )
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.event_bus.publish(event))
            except RuntimeError:
                asyncio.run(self.event_bus.publish(event))
