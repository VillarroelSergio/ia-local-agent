"""Tools for the Windows OS integration layer."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

try:
    from config import PROJECT_ROOT
    from os_integration import WindowsIntegrationRuntime
    from os_integration.models import AutomationStep, AutomationWorkflow, CaptureTarget, Rect, ScreenshotRequest
    from tooling import RiskLevel, ToolContext, ToolDefinition, ToolMetadata
except ModuleNotFoundError:
    from src.config import PROJECT_ROOT
    from src.os_integration import WindowsIntegrationRuntime
    from src.os_integration.models import AutomationStep, AutomationWorkflow, CaptureTarget, Rect, ScreenshotRequest
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


class ListWindowsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_empty_titles: bool = Field(default=False)
    limit: int = Field(default=50, ge=1, le=200)


class ListInstalledAppsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str | None = Field(default=None, max_length=120)
    limit: int = Field(default=50, ge=1, le=200)
    refresh: bool = Field(default=False)


class WindowTargetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handle: int | None = Field(default=None, ge=1)
    query: str | None = Field(default=None, max_length=160)


class MoveWindowInput(WindowTargetInput):
    left: int = Field()
    top: int = Field()


class ResizeWindowInput(MoveWindowInput):
    width: int = Field(ge=100, le=20000)
    height: int = Field(ge=100, le=20000)


class TileWindowsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queries: list[str] = Field(default_factory=list, max_length=8)
    handles: list[int] = Field(default_factory=list, max_length=8)
    layout: str = Field(default="horizontal", description="horizontal o vertical")
    monitor_index: int | None = Field(default=None, ge=0, le=16)


class SummarizeScreenInput(ScreenshotInput):
    language: str = Field(default="eng", max_length=16)
    max_chars: int = Field(default=4000, ge=500, le=12000)


class WorkflowStepInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(max_length=80)
    args: dict = Field(default_factory=dict)
    timeout_seconds: float = Field(default=10, ge=0.1, le=120)
    retry_count: int = Field(default=0, ge=0, le=5)
    require_confirmation: bool = Field(default=True)


class RunWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=120)
    steps: list[WorkflowStepInput] = Field(min_length=1, max_length=25)


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
        "app_id": window.app_id,
    }


def list_windows(args: ListWindowsInput, ctx: ToolContext):
    windows = get_runtime().window_manager.list_windows(
        include_empty_titles=args.include_empty_titles,
        limit=args.limit,
    )
    return {
        "count": len(windows),
        "windows": [
            {
                "handle": window.handle,
                "title": window.title,
                "process_name": window.process_name,
                "pid": window.pid,
                "rect": window.rect.__dict__ if window.rect else None,
                "monitor_index": window.monitor_index,
                "state": window.state.value,
                "app_id": window.app_id,
            }
            for window in windows
        ],
    }


def list_installed_applications(args: ListInstalledAppsInput, ctx: ToolContext):
    manager = get_runtime().application_manager
    apps = manager.find(args.query, limit=args.limit) if args.query else manager.list_installed_apps(
        refresh=args.refresh,
        limit=args.limit,
    )
    return {
        "count": len(apps),
        "applications": [
            {
                "name": app.name,
                "source": app.source,
                "kind": app.kind,
                "launch_path": app.launch_path,
            }
            for app in apps
        ],
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


def focus_window(args: WindowTargetInput, ctx: ToolContext):
    window = get_runtime().window_manager.focus_window(args.handle, query=args.query)
    return {"window": asdict(window)}


def move_window(args: MoveWindowInput, ctx: ToolContext):
    window = get_runtime().window_manager.move_window(args.handle, query=args.query, left=args.left, top=args.top)
    return {"window": asdict(window)}


def resize_window(args: ResizeWindowInput, ctx: ToolContext):
    window = get_runtime().window_manager.resize_window(
        args.handle,
        query=args.query,
        left=args.left,
        top=args.top,
        width=args.width,
        height=args.height,
    )
    return {"window": asdict(window)}


def maximize_window(args: WindowTargetInput, ctx: ToolContext):
    window = get_runtime().window_manager.maximize_window(args.handle, query=args.query)
    return {"window": asdict(window)}


def minimize_window(args: WindowTargetInput, ctx: ToolContext):
    window = get_runtime().window_manager.minimize_window(args.handle, query=args.query)
    return {"window": asdict(window)}


def close_window(args: WindowTargetInput, ctx: ToolContext):
    return get_runtime().window_manager.close_window(args.handle, query=args.query)


def tile_windows_layout(args: TileWindowsInput, ctx: ToolContext):
    windows = get_runtime().window_manager.tile_windows_layout(
        tuple(args.handles),
        queries=tuple(args.queries),
        layout=args.layout,
        monitor_index=args.monitor_index,
    )
    return {"count": len(windows), "windows": [asdict(window) for window in windows]}


def take_screenshot(args: ScreenshotInput, ctx: ToolContext):
    return capture_screenshot(args, ctx)


def take_region_screenshot(args: ScreenshotInput, ctx: ToolContext):
    return capture_screenshot(args.model_copy(update={"target": "region"}), ctx)


def take_window_screenshot(args: ScreenshotInput, ctx: ToolContext):
    return capture_screenshot(args.model_copy(update={"target": "active_window"}), ctx)


def ocr_active_window(args: OCRScreenInput, ctx: ToolContext):
    return ocr_screen(args.model_copy(update={"target": "active_window"}), ctx)


def ocr_region(args: OCRScreenInput, ctx: ToolContext):
    return ocr_screen(args.model_copy(update={"target": "region"}), ctx)


def summarize_screen(args: SummarizeScreenInput, ctx: ToolContext):
    result = get_runtime().ocr_service.read_screen(_build_request(args), language=args.language)
    text = result.text[:args.max_chars]
    return {
        "summary_input": text,
        "text_length": len(result.text),
        "provider": result.provider,
        "language": result.language,
        "note": "Resumen semantico final debe generarlo el LLM con este texto OCR y contexto de ventana.",
    }


async def run_windows_workflow(args: RunWorkflowInput, ctx: ToolContext):
    workflow = AutomationWorkflow(
        name=args.name,
        steps=tuple(
            AutomationStep(
                action=step.action,
                args=step.args,
                timeout_seconds=step.timeout_seconds,
                retry_count=step.retry_count,
                require_confirmation=step.require_confirmation,
            )
            for step in args.steps
        ),
    )
    results = await get_runtime().workflow_runner.run(workflow)
    return {
        "workflow_id": workflow.id,
        "ok": all(result.ok for result in results),
        "results": [asdict(result) for result in results],
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
            "take_screenshot",
            "Capability semantica: captura pantalla completa, monitor, ventana activa o region.",
            ScreenshotInput,
            take_screenshot,
            aliases=("capture_and_analyze_screen",),
            tags=("read_only", "vision", "semantic"),
            capabilities=("screen.capture", "screen.analyze"),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "take_region_screenshot",
            "Captura una region concreta de pantalla con validacion de coordenadas.",
            ScreenshotInput,
            take_region_screenshot,
            tags=("read_only", "vision", "semantic"),
            capabilities=("screen.capture.region",),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "take_window_screenshot",
            "Captura la ventana activa para analisis visual contextual.",
            ScreenshotInput,
            take_window_screenshot,
            tags=("read_only", "vision", "semantic"),
            capabilities=("screen.capture.window",),
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
            "ocr_active_window",
            "Extrae texto visible de la ventana activa mediante OCR local.",
            OCRScreenInput,
            ocr_active_window,
            aliases=("extract_visible_text",),
            tags=("read_only", "vision", "ocr", "semantic"),
            capabilities=("ocr.read", "window.summarize"),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "ocr_region",
            "Extrae texto visible de una region mediante OCR local.",
            OCRScreenInput,
            ocr_region,
            tags=("read_only", "vision", "ocr", "semantic"),
            capabilities=("ocr.read.region",),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "summarize_screen",
            "Prepara OCR y contexto de pantalla para que el LLM resuma la ventana o pantalla actual.",
            SummarizeScreenInput,
            summarize_screen,
            aliases=("summarize_active_window",),
            tags=("read_only", "vision", "ocr", "semantic"),
            capabilities=("screen.summarize", "window.summarize"),
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
            "list_windows",
            "Lista ventanas visibles actuales con titulo, proceso, PID, posicion, monitor y estado.",
            ListWindowsInput,
            list_windows,
            aliases=("current_windows", "open_windows"),
            tags=("read_only",),
            capabilities=("window.inspect",),
            risk_level=RiskLevel.SAFE,
        ),
        tool(
            "focus_window",
            "Enfoca una ventana por handle o busqueda semantica de titulo/proceso.",
            WindowTargetInput,
            focus_window,
            tags=("window_control", "semantic"),
            capabilities=("window.focus",),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
        ),
        tool(
            "move_window",
            "Mueve una ventana por handle o busqueda sin usar coordenadas de raton.",
            MoveWindowInput,
            move_window,
            aliases=("move_window_to_monitor",),
            tags=("window_control", "semantic"),
            capabilities=("window.move",),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
        ),
        tool(
            "resize_window",
            "Redimensiona una ventana por handle o busqueda.",
            ResizeWindowInput,
            resize_window,
            tags=("window_control", "semantic"),
            capabilities=("window.resize",),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
        ),
        tool(
            "maximize_window",
            "Maximiza una ventana por handle o busqueda.",
            WindowTargetInput,
            maximize_window,
            tags=("window_control", "semantic"),
            capabilities=("window.maximize",),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
        ),
        tool(
            "minimize_window",
            "Minimiza una ventana por handle o busqueda.",
            WindowTargetInput,
            minimize_window,
            tags=("window_control", "semantic"),
            capabilities=("window.minimize",),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
        ),
        tool(
            "close_window",
            "Solicita cerrar una ventana por handle o busqueda.",
            WindowTargetInput,
            close_window,
            tags=("window_control", "semantic"),
            capabilities=("window.close",),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
        ),
        tool(
            "tile_windows_layout",
            "Organiza varias ventanas en layout horizontal o vertical dentro de un monitor.",
            TileWindowsInput,
            tile_windows_layout,
            aliases=("organize_windows",),
            tags=("window_control", "semantic"),
            capabilities=("window.tile", "window.organize"),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
        ),
        tool(
            "list_installed_applications",
            "Lista o busca aplicaciones instaladas resolubles por el agente.",
            ListInstalledAppsInput,
            list_installed_applications,
            aliases=("list_apps", "installed_apps"),
            tags=("read_only",),
            capabilities=("application.inspect",),
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
        tool(
            "run_windows_workflow",
            "Ejecuta un workflow Windows compuesto por pasos semanticos y acciones internas.",
            RunWorkflowInput,
            run_windows_workflow,
            aliases=("automate_repetitive_task",),
            tags=("workflow", "semantic"),
            capabilities=("workflow.run", "automation.compose"),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
            timeout_seconds=120,
        ),
    ]
