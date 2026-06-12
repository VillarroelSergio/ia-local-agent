from dataclasses import asdict
from urllib.parse import urljoin

from fastapi import APIRouter
from openai import OpenAI

from src.api.dependencies import local_agent
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


@router.get("/system/windows")
async def windows(limit: int = 80):
    """Return safe metadata for visible windows."""
    manager = WindowManager()
    items = []
    for window in manager.list_windows(include_empty_titles=False, limit=limit):
        if _is_own_window(window):
            continue
        payload = _window_payload(manager, window)
        if payload["window"]:
            items.append(payload["window"])
    return {"count": len(items), "windows": items}


@router.get("/system/window/{handle}")
async def window_by_handle(handle: int):
    """Return safe metadata for a specific HWND."""
    manager = WindowManager()
    try:
        window = manager.get_window_info(handle)
    except Exception as error:
        return {"available": False, "allowed": False, "reason": str(error), "window": None}
    return _window_payload(manager, window)


@router.get("/system/lmstudio")
async def lmstudio_diagnostics():
    """Diagnose LM Studio connectivity and configured model."""
    agent = local_agent()
    settings = agent.settings
    base_url = settings.lmstudio_base_url.rstrip("/")
    result = {
        "ok": False,
        "base_url": settings.lmstudio_base_url,
        "configured_model": settings.default_model,
        "models_url": urljoin(f"{base_url}/", "models"),
        "models": [],
        "model_found": False,
        "error": None,
        "last_provider_metrics": getattr(agent.provider, "last_metrics", None),
    }
    try:
        client = OpenAI(base_url=settings.lmstudio_base_url, api_key=settings.lmstudio_api_key)
        models = client.models.list()
        ids = [item.id for item in models.data]
        result.update({
            "ok": True,
            "models": ids,
            "model_found": settings.default_model in ids,
        })
    except Exception as error:
        result["error"] = str(error)
    return result
