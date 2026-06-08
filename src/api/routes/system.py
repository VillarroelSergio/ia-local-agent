from dataclasses import asdict

from fastapi import APIRouter

from src.os_integration.security import OSScope
from src.os_integration.windows import WindowManager

router = APIRouter()

OWN_WINDOW_TITLE_MARKERS = ("ia local agent",)
OWN_PROCESS_NAMES = ("ia-local-agent-desktop", "ia-local-agent-api")


def _is_own_window(window) -> bool:
    title = (window.title or "").lower()
    process = (window.process_name or "").lower()
    return any(marker in title for marker in OWN_WINDOW_TITLE_MARKERS) or any(name in process for name in OWN_PROCESS_NAMES)


def _window_payload(manager: WindowManager, window) -> dict:
    decision = manager.ensure_window_allowed(window, OSScope.WINDOW_INSPECT)
    if not decision.allowed:
        return {
            "available": True,
            "allowed": False,
            "reason": decision.reason,
            "window": {
                "handle": window.handle,
                "title": None,
                "process_name": window.process_name,
                "pid": window.pid,
                "state": window.state.value,
                "monitor_index": window.monitor_index,
                "sensitive": True,
            },
        }

    data = asdict(window)
    if window.state:
        data["state"] = window.state.value
    data["sensitive"] = False
    return {
        "available": True,
        "allowed": True,
        "reason": decision.reason,
        "window": data,
    }


def _active_window_payload(*, exclude_own: bool = False) -> dict:
    manager = WindowManager()
    window = manager.get_active_window()
    if exclude_own and window is not None and _is_own_window(window):
        window = next((item for item in manager.list_windows(limit=25) if not _is_own_window(item)), None)

    if window is None:
        return {
            "available": False,
            "allowed": False,
            "reason": "No hay ventana activa o WinAPI no esta disponible.",
            "window": None,
        }

    return _window_payload(manager, window)


@router.get("/system/active-window")
async def active_window(exclude_own: bool = False):
    """Return safe metadata for the current foreground window."""
    return _active_window_payload(exclude_own=exclude_own)
