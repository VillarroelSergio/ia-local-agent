"""Windows OS integration layer for local agent runtimes."""

from .automation import AutomationEngine, WorkflowExecutor
from .events import EventBus, EventPriority, EventType, OSEvent
from .hotkeys import HotkeyManager
from .lifecycle import WindowsIntegrationRuntime
from .ocr import OCRService
from .screenshots import ScreenshotService
from .security import OSSecurityPolicy
from .windows import WindowManager

__all__ = [
    "AutomationEngine",
    "EventBus",
    "EventPriority",
    "EventType",
    "HotkeyManager",
    "OCRService",
    "OSEvent",
    "OSSecurityPolicy",
    "ScreenshotService",
    "WindowManager",
    "WindowsIntegrationRuntime",
    "WorkflowExecutor",
]
