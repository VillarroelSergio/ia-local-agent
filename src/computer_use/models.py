"""Typed models for the Computer Use Runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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


TERMINAL_STATUSES = frozenset({
    ComputerUseStatus.COMPLETED,
    ComputerUseStatus.FAILED,
    ComputerUseStatus.ABORTED,
    ComputerUseStatus.CANCELLED,
})

ALLOWED_STATUS_TRANSITIONS: dict[ComputerUseStatus, frozenset[ComputerUseStatus]] = {
    ComputerUseStatus.CREATED: frozenset({ComputerUseStatus.RUNNING, ComputerUseStatus.CANCELLED}),
    ComputerUseStatus.RUNNING: frozenset({
        ComputerUseStatus.WAITING_CONFIRMATION,
        ComputerUseStatus.COMPLETED,
        ComputerUseStatus.FAILED,
        ComputerUseStatus.ABORTED,
        ComputerUseStatus.CANCELLED,
    }),
    ComputerUseStatus.WAITING_CONFIRMATION: frozenset({
        ComputerUseStatus.RUNNING,
        ComputerUseStatus.CANCELLED,
        ComputerUseStatus.FAILED,
    }),
    ComputerUseStatus.COMPLETED: frozenset(),
    ComputerUseStatus.FAILED: frozenset(),
    ComputerUseStatus.ABORTED: frozenset(),
    ComputerUseStatus.CANCELLED: frozenset(),
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    timestamp: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    limitations: tuple[str, ...] = ()
    sensitive_content_detected: bool = False
    blocked_by_policy: bool = False

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
    created_at: datetime = field(default_factory=utc_now)


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
    verifications: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    policy_decisions: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] | None = None
    active_window: dict[str, Any] | None = None
    current_step_index: int = 0
    correlation_id: str = field(default_factory=lambda: f"corr_{uuid4().hex}")
    status: ComputerUseStatus = ComputerUseStatus.CREATED
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    error: str | None = None

    def record_observation(self, observation: DesktopObservation) -> None:
        self.observations.append(observation.to_dict())
        self.updated_at = utc_now()

    def record_action(self, action: dict[str, Any]) -> None:
        self.actions.append(_jsonable(action))
        self.updated_at = utc_now()

    def record_verification(self, verification: dict[str, Any]) -> None:
        self.verifications.append(_jsonable(verification))
        self.updated_at = utc_now()

    def record_error(self, message: str, *, code: str = "computer_use_error") -> None:
        self.error = message
        self.errors.append({"code": code, "message": message, "timestamp": utc_now().isoformat()})
        self.updated_at = utc_now()

    def transition(self, status: ComputerUseStatus, *, error: str | None = None) -> None:
        if status == self.status:
            return
        if status not in ALLOWED_STATUS_TRANSITIONS[self.status]:
            raise ValueError(f"Transicion de sesion invalida: {self.status.value} -> {status.value}")
        self.status = status
        self.error = error
        self.updated_at = utc_now()
        if status in TERMINAL_STATUSES:
            self.completed_at = self.updated_at
        if status == ComputerUseStatus.CANCELLED:
            self.cancelled_at = self.updated_at

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
