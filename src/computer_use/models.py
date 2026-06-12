"""Typed models for the Computer Use Runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

try:
    from os_integration.models import WindowInfo
except ModuleNotFoundError:
    from src.os_integration.models import WindowInfo


class ComputerUseStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    CANCELLED = "cancelled"


class ObservationSource(str, Enum):
    WINDOW_MANAGER = "window_manager"
    UI_AUTOMATION = "ui_automation"
    OCR = "ocr"
    VISION = "vision"
    NONE = "none"


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class UIControl:
    name: str
    control_type: str
    automation_id: str | None = None
    class_name: str | None = None
    value: str | None = None
    enabled: bool = True
    visible: bool = True
    is_password: bool = False
    rect: dict[str, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DesktopObservation:
    active_window: WindowInfo | None = None
    open_windows: tuple[WindowInfo, ...] = ()
    controls: tuple[UIControl, ...] = ()
    visible_text: str = ""
    screen_summary: str = ""
    source_order: tuple[ObservationSource, ...] = ()
    used_sources: tuple[ObservationSource, ...] = ()
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class PlanStep:
    capability: str
    description: str
    args: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)
    status: PlanStepStatus = PlanStepStatus.PENDING
    id: str = field(default_factory=lambda: f"plan_step_{uuid4().hex}")


@dataclass(frozen=True)
class Plan:
    goal: str
    steps: tuple[PlanStep, ...]
    rationale: str = ""
    id: str = field(default_factory=lambda: f"plan_{uuid4().hex}")
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ExecutionGraph:
    plan_id: str
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComputerUseSession:
    goal: str
    id: str = field(default_factory=lambda: f"cu_{uuid4().hex}")
    state: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    status: ComputerUseStatus = ComputerUseStatus.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    error: str | None = None

    def record_observation(self, observation: DesktopObservation) -> None:
        self.observations.append(observation.to_dict())
        self.updated_at = datetime.now()

    def record_action(self, action: dict[str, Any]) -> None:
        self.actions.append(_jsonable(action))
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value
