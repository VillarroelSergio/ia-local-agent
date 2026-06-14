"""Window inspection and focus monitoring for Windows."""

from __future__ import annotations

import asyncio
import ctypes
from ctypes import wintypes
from dataclasses import asdict

import psutil

from .events import EventBus, EventType, OSEvent
from .models import MonitorInfo, Rect, WindowInfo, WindowState
from .security import OSScope, OSSecurityPolicy


user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_RESTORE = 9
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040
WM_CLOSE = 0x0010


class WindowManager:
    def __init__(self, *, security: OSSecurityPolicy | None = None, event_bus: EventBus | None = None):
        self.security = security or OSSecurityPolicy()
        self.event_bus = event_bus
        self._monitor_task: asyncio.Task | None = None
        self._last_handle: int | None = None

    def get_active_window(self) -> WindowInfo | None:
        if user32 is None:
            return None
        raw_handle = user32.GetForegroundWindow()
        if not raw_handle:
            return None
        handle = int(raw_handle)
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

    def list_windows(self, *, include_empty_titles: bool = False, limit: int = 100) -> tuple[WindowInfo, ...]:
        if user32 is None:
            return ()
        windows: list[WindowInfo] = []

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def callback(handle, data):
            if len(windows) >= limit:
                return False
            if not user32.IsWindowVisible(handle):
                return True
            title = self._get_window_title(int(handle))
            if not include_empty_titles and not title.strip():
                return True
            info = self.get_window_info(int(handle))
            decision = self.security.evaluate_window(info)
            if decision.allowed:
                windows.append(info)
            return True

        user32.EnumWindows(EnumWindowsProc(callback), 0)
        return tuple(windows)

    def find_windows(self, query: str, *, limit: int = 10) -> tuple[WindowInfo, ...]:
        normalized = query.strip().lower()
        if not normalized:
            return ()
        matches = []
        for window in self.list_windows(include_empty_titles=False, limit=300):
            haystack = " ".join(
                part for part in (window.title, window.process_name, window.app_id) if part
            ).lower()
            if normalized in haystack:
                matches.append(window)
                if len(matches) >= limit:
                    break
        return tuple(matches)

    def focus_window(self, handle: int | None = None, *, query: str | None = None) -> WindowInfo:
        window = self._resolve_window(handle, query)
        decision = self.security.evaluate_scope(OSScope.WINDOW_CONTROL, window)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        if user32 is None or window.handle is None:
            raise RuntimeError("WinAPI no disponible para enfocar ventanas.")
        if user32.IsIconic(window.handle):
            user32.ShowWindow(window.handle, SW_RESTORE)
        user32.SetForegroundWindow(window.handle)
        return self.get_window_info(window.handle)

    def move_window(self, handle: int | None = None, *, query: str | None = None, left: int, top: int) -> WindowInfo:
        window = self._resolve_window(handle, query)
        rect = window.rect
        if rect is None:
            raise ValueError("La ventana no tiene rectangulo disponible.")
        return self.resize_window(window.handle, left=left, top=top, width=rect.width, height=rect.height)

    def resize_window(
        self,
        handle: int | None = None,
        *,
        query: str | None = None,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> WindowInfo:
        window = self._resolve_window(handle, query)
        decision = self.security.evaluate_scope(OSScope.WINDOW_CONTROL, window)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        if user32 is None or window.handle is None:
            raise RuntimeError("WinAPI no disponible para redimensionar ventanas.")
        if user32.IsZoomed(window.handle) or user32.IsIconic(window.handle):
            user32.ShowWindow(window.handle, SW_RESTORE)
        ok = user32.SetWindowPos(
            window.handle,
            0,
            int(left),
            int(top),
            int(width),
            int(height),
            SWP_NOZORDER | SWP_SHOWWINDOW,
        )
        if not ok:
            raise RuntimeError("Windows no permitio mover/redimensionar la ventana.")
        return self.get_window_info(window.handle)

    def maximize_window(self, handle: int | None = None, *, query: str | None = None) -> WindowInfo:
        return self._show_window(handle, query=query, command=SW_SHOWMAXIMIZED)

    def minimize_window(self, handle: int | None = None, *, query: str | None = None) -> WindowInfo:
        return self._show_window(handle, query=query, command=SW_SHOWMINIMIZED)

    def close_window(self, handle: int | None = None, *, query: str | None = None) -> dict:
        window = self._resolve_window(handle, query)
        decision = self.security.evaluate_scope(OSScope.WINDOW_CONTROL, window)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        if user32 is None or window.handle is None:
            raise RuntimeError("WinAPI no disponible para cerrar ventanas.")
        ok = bool(user32.PostMessageW(window.handle, WM_CLOSE, 0, 0))
        return {"closed_requested": ok, "window": asdict(window)}

    def tile_windows_layout(
        self,
        handles: tuple[int, ...] = (),
        *,
        queries: tuple[str, ...] = (),
        layout: str = "horizontal",
        monitor_index: int | None = None,
    ) -> tuple[WindowInfo, ...]:
        targets = [self._resolve_window(handle, None) for handle in handles]
        targets.extend(self._resolve_window(None, query) for query in queries)
        if not targets:
            targets = list(self.list_windows(limit=2)[:2])
        if not targets:
            return ()

        monitors = self.list_monitors()
        monitor = monitors[monitor_index or 0] if monitors else MonitorInfo(0, Rect(0, 0, 1920, 1080), True)
        area = monitor.rect
        count = len(targets)
        results: list[WindowInfo] = []
        for index, window in enumerate(targets):
            if layout == "vertical":
                width = area.width
                height = max(1, area.height // count)
                left = area.left
                top = area.top + index * height
            else:
                width = max(1, area.width // count)
                height = area.height
                left = area.left + index * width
                top = area.top
            results.append(self.resize_window(window.handle, left=left, top=top, width=width, height=height))
        return tuple(results)

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

    def _show_window(self, handle: int | None, *, query: str | None, command: int) -> WindowInfo:
        window = self._resolve_window(handle, query)
        decision = self.security.evaluate_scope(OSScope.WINDOW_CONTROL, window)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        if user32 is None or window.handle is None:
            raise RuntimeError("WinAPI no disponible para controlar ventanas.")
        if not user32.ShowWindow(window.handle, command):
            # ShowWindow returns previous visibility, so false is not always a failure.
            pass
        return self.get_window_info(window.handle)

    def _resolve_window(self, handle: int | None, query: str | None) -> WindowInfo:
        if handle:
            return self.get_window_info(handle)
        if query:
            matches = self.find_windows(query, limit=2)
            if not matches:
                raise ValueError(f"No se encontro ventana para: {query}")
            if len(matches) > 1:
                titles = [window.title for window in matches]
                raise ValueError(f"Ventana ambigua para '{query}': {titles}")
            return matches[0]
        active = self.get_active_window()
        if active is None:
            raise ValueError("No hay ventana activa.")
        return active

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
