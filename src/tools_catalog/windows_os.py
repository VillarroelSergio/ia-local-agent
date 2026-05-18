"""Tools for the Windows OS integration layer."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

try:
    from config import PROJECT_ROOT
    from os_integration import WindowsIntegrationRuntime
    from os_integration.models import CaptureTarget, Rect, ScreenshotRequest
    from tooling import RiskLevel, ToolContext, ToolDefinition, ToolMetadata
except ModuleNotFoundError:
    from src.config import PROJECT_ROOT
    from src.os_integration import WindowsIntegrationRuntime
    from src.os_integration.models import CaptureTarget, Rect, ScreenshotRequest
    from src.tooling import RiskLevel, ToolContext, ToolDefinition, ToolMetadata


_RUNTIME: WindowsIntegrationRuntime | None = None


class ScreenshotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = Field(default="full_screen", description="full_screen, monitor, active_window o region.")
    monitor_index: int | None = Field(default=None, ge=0, le=16)
    left: int | None = Field(default=None)
    top: int | None = Field(default=None)
    width: int | None = Field(default=None, ge=1, le=10000)
    height: int | None = Field(default=None, ge=1, le=10000)
    save: bool = Field(default=True, description="Guarda la captura en data/os_captures.")
    compress: bool = Field(default=False)


class OCRScreenInput(ScreenshotInput):
    language: str = Field(default="eng", max_length=16)


def get_runtime() -> WindowsIntegrationRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = WindowsIntegrationRuntime.build()
    return _RUNTIME


def _build_request(args: ScreenshotInput) -> ScreenshotRequest:
    try:
        target = CaptureTarget(args.target)
    except ValueError as error:
        raise ValueError("target debe ser full_screen, monitor, active_window o region.") from error
    region = None
    if target == CaptureTarget.REGION:
        missing = [name for name in ("left", "top", "width", "height") if getattr(args, name) is None]
        if missing:
            raise ValueError(f"Faltan campos para region: {', '.join(missing)}")
        region = Rect(args.left, args.top, args.width, args.height)
    save_path = None
    if args.save:
        target_dir = PROJECT_ROOT / "data" / "os_captures"
        target_dir.mkdir(parents=True, exist_ok=True)
        save_path = target_dir / "latest_screenshot.jpg"
    return ScreenshotRequest(
        target=target,
        monitor_index=args.monitor_index,
        region=region,
        compress=args.compress,
        save_path=save_path,
    )


def capture_screenshot(args: ScreenshotInput, ctx: ToolContext):
    result = get_runtime().screenshot_service.capture(_build_request(args))
    return {
        "target": result.target.value,
        "rect": result.rect.__dict__,
        "cached": result.cached,
        "path": str(result.path) if result.path else None,
        "monitors": [
            {"index": monitor.index, "rect": monitor.rect.__dict__, "primary": monitor.primary}
            for monitor in result.monitors
        ],
        "metadata": result.metadata,
    }


def ocr_screen(args: OCRScreenInput, ctx: ToolContext):
    request = _build_request(args)
    result = get_runtime().ocr_service.read_screen(request, language=args.language)
    return {
        "text": result.text[:8000],
        "provider": result.provider,
        "language": result.language,
        "duration_ms": result.duration_ms,
        "boxes": [
            {"text": box.text, "confidence": box.confidence, "rect": box.rect.__dict__}
            for box in result.boxes[:200]
        ],
        "metadata": result.metadata,
    }


def get_active_window(args: BaseModel, ctx: ToolContext):
    window = get_runtime().window_manager.get_active_window()
    if window is None:
        return {"active_window": None}
    return {
        "handle": window.handle,
        "title": window.title,
        "process_name": window.process_name,
        "pid": window.pid,
        "rect": window.rect.__dict__ if window.rect else None,
        "monitor_index": window.monitor_index,
        "state": window.state.value,
        "executable_path": window.executable_path,
        "app_id": window.app_id,
    }


def list_monitors(args: BaseModel, ctx: ToolContext):
    monitors = get_runtime().window_manager.list_monitors()
    return {
        "count": len(monitors),
        "monitors": [
            {"index": monitor.index, "rect": monitor.rect.__dict__, "primary": monitor.primary, "name": monitor.name}
            for monitor in monitors
        ],
    }


def tool(name, description, schema, handler, *, aliases=(), tags=(), capabilities=(), risk_level=RiskLevel.READ_ONLY, requires_confirmation=False, timeout_seconds=10):
    return ToolDefinition(
        metadata=ToolMetadata(
            name=name,
            description=description,
            category="windows_os",
            aliases=aliases,
            tags=tags,
            capabilities=capabilities,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            timeout_seconds=timeout_seconds,
        ),
        input_schema=schema,
        handler=handler,
    )


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def build_windows_os_tool_definitions():
    return [
        tool(
            "capture_screenshot",
            "Captura pantalla completa, monitor, ventana activa o region y opcionalmente guarda la imagen.",
            ScreenshotInput,
            capture_screenshot,
            aliases=("screenshot",),
            tags=("read_only", "vision"),
            capabilities=("screen.capture",),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "ocr_screen",
            "Ejecuta OCR local sobre pantalla, monitor, ventana activa o region.",
            OCRScreenInput,
            ocr_screen,
            tags=("read_only", "vision", "ocr"),
            capabilities=("ocr.read",),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "get_active_window",
            "Obtiene titulo, proceso, PID, posicion y estado de la ventana activa.",
            EmptyInput,
            get_active_window,
            aliases=("active_window",),
            tags=("read_only",),
            capabilities=("window.inspect",),
            risk_level=RiskLevel.SAFE,
        ),
        tool(
            "list_monitors",
            "Lista monitores detectados con rectangulos virtual-screen.",
            EmptyInput,
            list_monitors,
            tags=("read_only",),
            capabilities=("monitor.inspect",),
            risk_level=RiskLevel.SAFE,
        ),
    ]
