"""Window inspection and focus monitoring for Windows."""

from __future__ import annotations

import asyncio
import ctypes
from ctypes import wintypes
from typing import Callable

import psutil

from .events import EventBus, EventType, OSEvent
from .models import MonitorInfo, Rect, WindowInfo, WindowState
from .security import OSScope, OSSecurityPolicy


user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None


class WindowManager:
    def __init__(self, *, security: OSSecurityPolicy | None = None, event_bus: EventBus | None = None):
        self.security = security or OSSecurityPolicy()
        self.event_bus = event_bus
        self._monitor_task: asyncio.Task | None = None
        self._last_handle: int | None = None

    def get_active_window(self) -> WindowInfo | None:
        if user32 is None:
            return None
        handle = int(user32.GetForegroundWindow())
        if not handle:
            return None
        return self.get_window_info(handle)

    def get_window_info(self, handle: int) -> WindowInfo:
        title = self._get_window_title(handle)
        pid = self._get_window_pid(handle)
        process_name = None
        executable_path = None
        if pid:
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                executable_path = process.exe()
            except (psutil.Error, OSError):
                pass
        rect = self._get_window_rect(handle)
        state = self._get_window_state(handle, rect)
        monitor_index = self._find_monitor_index(rect) if rect else None
        return WindowInfo(
            handle=handle,
            title=title,
            process_name=process_name,
            pid=pid,
            rect=rect,
            monitor_index=monitor_index,
            state=state,
            executable_path=executable_path,
            app_id=process_name,
        )

    def list_monitors(self) -> tuple[MonitorInfo, ...]:
        if user32 is None:
            return ()
        monitors: list[MonitorInfo] = []

        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )

        def callback(monitor, hdc, rect_pointer, data):
            rect = rect_pointer.contents
            monitors.append(MonitorInfo(
                index=len(monitors),
                rect=Rect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top),
                primary=len(monitors) == 0,
            ))
            return 1

        user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(callback), 0)
        return tuple(monitors)

    async def start_focus_monitor(self, *, interval_seconds: float = 0.5) -> None:
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._focus_loop(interval_seconds), name="window-focus-monitor")

    async def stop_focus_monitor(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _focus_loop(self, interval_seconds: float) -> None:
        while True:
            active = self.get_active_window()
            handle = active.handle if active else None
            if handle != self._last_handle:
                self._last_handle = handle
                if self.event_bus and active:
                    await self.event_bus.publish(OSEvent(EventType.WINDOW_FOCUS_CHANGED, {
                        "handle": active.handle,
                        "title": active.title,
                        "process_name": active.process_name,
                        "pid": active.pid,
                        "state": active.state.value,
                    }))
            await asyncio.sleep(interval_seconds)

    def ensure_window_allowed(self, window: WindowInfo | None, scope: OSScope):
        return self.security.evaluate_scope(scope, window)

    def _get_window_title(self, handle: int) -> str:
        length = user32.GetWindowTextLengthW(handle)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, buffer, length + 1)
        return buffer.value

    def _get_window_pid(self, handle: int) -> int | None:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        return int(pid.value) if pid.value else None

    def _get_window_rect(self, handle: int) -> Rect | None:
        rect = wintypes.RECT()
        if not user32.GetWindowRect(handle, ctypes.byref(rect)):
            return None
        return Rect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)

    def _get_window_state(self, handle: int, rect: Rect | None) -> WindowState:
        if user32.IsIconic(handle):
            return WindowState.MINIMIZED
        if user32.IsZoomed(handle):
            return WindowState.MAXIMIZED
        if rect:
            for monitor in self.list_monitors():
                if rect.left <= monitor.rect.left and rect.top <= monitor.rect.top and rect.right >= monitor.rect.right and rect.bottom >= monitor.rect.bottom:
                    return WindowState.FULLSCREEN
        return WindowState.NORMAL

    def _find_monitor_index(self, rect: Rect | None) -> int | None:
        if rect is None:
            return None
        center_x = rect.left + rect.width // 2
        center_y = rect.top + rect.height // 2
        for monitor in self.list_monitors():
            if monitor.rect.left <= center_x <= monitor.rect.right and monitor.rect.top <= center_y <= monitor.rect.bottom:
                return monitor.index
        return None
