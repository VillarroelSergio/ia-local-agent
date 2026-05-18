"""Typed DTOs shared by the Windows integration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


class CaptureTarget(str, Enum):
    FULL_SCREEN = "full_screen"
    MONITOR = "monitor"
    ACTIVE_WINDOW = "active_window"
    REGION = "region"


class WindowState(str, Enum):
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"
    UNKNOWN = "unknown"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom


@dataclass(frozen=True)
class MonitorInfo:
    index: int
    rect: Rect
    primary: bool = False
    dpi_scale: float | None = None
    name: str | None = None


@dataclass(frozen=True)
class WindowInfo:
    handle: int | None
    title: str
    process_name: str | None
    pid: int | None
    rect: Rect | None
    monitor_index: int | None
    state: WindowState = WindowState.UNKNOWN
    executable_path: str | None = None
    app_id: str | None = None


@dataclass(frozen=True)
class ScreenshotRequest:
    target: CaptureTarget = CaptureTarget.FULL_SCREEN
    monitor_index: int | None = None
    window_handle: int | None = None
    region: Rect | None = None
    include_cursor: bool = False
    max_age_ms: int = 250
    compress: bool = False
    quality: int = 85
    save_path: Path | None = None


@dataclass(frozen=True)
class ScreenshotResult:
    image: Any
    target: CaptureTarget
    rect: Rect
    monitors: tuple[MonitorInfo, ...]
    cached: bool = False
    path: Path | None = None
    captured_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OCRBox:
    text: str
    confidence: float
    rect: Rect
    block_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OCRResult:
    text: str
    boxes: tuple[OCRBox, ...]
    provider: str
    language: str
    duration_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AutomationStep:
    action: str
    args: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 10
    retry_count: int = 0
    require_confirmation: bool = True
    id: str = field(default_factory=lambda: f"step_{uuid4().hex}")


@dataclass(frozen=True)
class WorkflowCondition:
    kind: str
    args: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 10
    poll_interval_seconds: float = 0.25


@dataclass(frozen=True)
class ActionHistoryEntry:
    workflow_id: str
    step_id: str
    action: str
    ok: bool
    duration_ms: int
    result: Any | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class AutomationWorkflow:
    name: str
    steps: tuple[AutomationStep, ...]
    id: str = field(default_factory=lambda: f"workflow_{uuid4().hex}")
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScheduledTask:
    name: str
    workflow: AutomationWorkflow
    trigger: str = "manual"
    interval_seconds: float | None = None
    enabled: bool = True
    id: str = field(default_factory=lambda: f"task_{uuid4().hex}")
    status: TaskStatus = TaskStatus.PENDING
    next_run_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HotkeyBinding:
    name: str
    keys: str
    action: str
    enabled: bool = True
    priority: int = 100
    requires_confirmation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
