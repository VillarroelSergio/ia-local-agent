"""Tools for the Computer Use Runtime."""

from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel, ConfigDict, Field

try:
    from computer_use import ComputerUseEngine
    from computer_use.observer import UIAutomationService
    from tooling import RiskLevel, ToolContext, ToolDefinition, ToolMetadata
except ModuleNotFoundError:
    from src.computer_use import ComputerUseEngine
    from src.computer_use.observer import UIAutomationService
    from src.tooling import RiskLevel, ToolContext, ToolDefinition, ToolMetadata


_ENGINE: ComputerUseEngine | None = None


class ComputerUseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=1000)
    max_iterations: int = Field(default=3, ge=1, le=10)


class ObserveDesktopInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_ocr: bool = Field(default=False, description="OCR solo bajo peticion explicita.")


class ObserveWindowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handle: int | None = Field(default=None, ge=1)
    include_ocr: bool = Field(default=False)


class FindUIControlInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    window_handle: int | None = Field(default=None, ge=1)


class InvokeUIControlInput(FindUIControlInput):
    pass


class SetUITextInput(FindUIControlInput):
    text: str = Field(min_length=1, max_length=4000)


class AnalyzeApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=200)
    include_ocr: bool = Field(default=False)


class ExecuteWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1, max_length=1000)
    max_iterations: int = Field(default=3, ge=1, le=10)


def get_engine() -> ComputerUseEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ComputerUseEngine()
    return _ENGINE


async def computer_use(args: ComputerUseInput, ctx: ToolContext):
    session = await get_engine().run_goal(args.goal, max_iterations=args.max_iterations)
    return session.to_dict()


def observe_desktop(args: ObserveDesktopInput, ctx: ToolContext):
    observation = get_engine().observer.observe_desktop(include_ocr=args.include_ocr)
    return observation.to_dict()


def observe_window(args: ObserveWindowInput, ctx: ToolContext):
    observation = get_engine().observer.observe_window(args.handle, include_ocr=args.include_ocr)
    return observation.to_dict()


def find_ui_control(args: FindUIControlInput, ctx: ToolContext):
    service = UIAutomationService()
    control = service.find_control_by_name(args.name, window_handle=args.window_handle)
    return {"control": asdict(control) if control else None, "uia_available": service.available}


def invoke_ui_control(args: InvokeUIControlInput, ctx: ToolContext):
    service = UIAutomationService()
    return service.invoke_named_control(args.name, window_handle=args.window_handle)


def set_ui_text(args: SetUITextInput, ctx: ToolContext):
    service = UIAutomationService()
    controls = service.find_inputs(window_handle=args.window_handle, query=args.name)
    if not controls:
        raise ValueError("Campo UIA no encontrado.")
    return service.set_text(controls[0], args.text)


async def execute_workflow(args: ExecuteWorkflowInput, ctx: ToolContext):
    session = await get_engine().run_goal(args.goal, max_iterations=args.max_iterations)
    return session.to_dict()


def analyze_application(args: AnalyzeApplicationInput, ctx: ToolContext):
    observation = get_engine().observer.observe_application(args.query, include_ocr=args.include_ocr)
    return observation.to_dict()


async def automate_application(args: ExecuteWorkflowInput, ctx: ToolContext):
    session = await get_engine().run_goal(args.goal, max_iterations=args.max_iterations)
    return session.to_dict()


def tool(
    name,
    description,
    schema,
    handler,
    *,
    aliases=(),
    tags=(),
    capabilities=(),
    risk_level=RiskLevel.READ_ONLY,
    requires_confirmation=False,
    timeout_seconds=30,
):
    return ToolDefinition(
        metadata=ToolMetadata(
            name=name,
            description=description,
            category="computer_use",
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


def build_computer_use_tool_definitions():
    return [
        tool(
            "computer_use",
            "Ejecuta un objetivo mediante ciclo Observe-Plan-Act-Verify-Repeat.",
            ComputerUseInput,
            computer_use,
            tags=("semantic", "workflow", "computer_use"),
            capabilities=("computer_use.run", "automation.compose"),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
            timeout_seconds=120,
        ),
        tool(
            "observe_desktop",
            "Observa el escritorio con prioridad WindowManager, UI Automation y OCR explicito.",
            ObserveDesktopInput,
            observe_desktop,
            tags=("read_only", "computer_use"),
            capabilities=("computer_use.observe", "window.inspect"),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "observe_window",
            "Observa una ventana concreta o la activa sin capturas persistentes.",
            ObserveWindowInput,
            observe_window,
            tags=("read_only", "computer_use"),
            capabilities=("computer_use.observe.window", "window.inspect"),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "find_ui_control",
            "Busca controles UIA por nombre para preferir acciones semanticas sobre coordenadas.",
            FindUIControlInput,
            find_ui_control,
            tags=("read_only", "computer_use", "uia"),
            capabilities=("ui_automation.find_control",),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "click_ui_control",
            "Invoca un control UIA por nombre tras verificar ventana, foco e identidad.",
            InvokeUIControlInput,
            invoke_ui_control,
            tags=("computer_use", "uia", "semantic"),
            capabilities=("ui_automation.invoke",),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
        ),
        tool(
            "fill_text_field",
            "Escribe texto en un campo UIA no sensible tras verificar ventana, foco e identidad.",
            SetUITextInput,
            set_ui_text,
            tags=("computer_use", "uia", "semantic"),
            capabilities=("ui_automation.set_text",),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
        ),
        tool(
            "execute_workflow",
            "Ejecuta un objetivo de Computer Use delegando en WorkflowRunner.",
            ExecuteWorkflowInput,
            execute_workflow,
            tags=("workflow", "computer_use"),
            capabilities=("workflow.run", "computer_use.run"),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
            timeout_seconds=120,
        ),
        tool(
            "analyze_application",
            "Observa una aplicacion por titulo/proceso y devuelve estado estructurado.",
            AnalyzeApplicationInput,
            analyze_application,
            tags=("read_only", "computer_use"),
            capabilities=("application.analyze", "computer_use.observe"),
            risk_level=RiskLevel.READ_ONLY,
        ),
        tool(
            "automate_application",
            "Automatiza una aplicacion mediante capacidades semanticas y verificacion.",
            ExecuteWorkflowInput,
            automate_application,
            tags=("workflow", "computer_use"),
            capabilities=("application.automate", "computer_use.run"),
            risk_level=RiskLevel.USER_CONFIRM,
            requires_confirmation=True,
            timeout_seconds=120,
        ),
    ]
