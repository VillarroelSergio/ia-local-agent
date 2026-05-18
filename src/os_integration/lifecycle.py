"""Lifecycle manager wiring Windows integration services together."""

from __future__ import annotations

from dataclasses import dataclass

from .apps import ApplicationManager
from .automation import AutomationEngine, WorkflowRunner
from .events import EventBus
from .hotkeys import HotkeyManager
from .ocr import OCRService
from .screenshots import ScreenshotService
from .security import OSSecurityPolicy
from .scheduler import TaskScheduler
from .windows import WindowManager


@dataclass
class WindowsIntegrationRuntime:
    security: OSSecurityPolicy
    event_bus: EventBus
    window_manager: WindowManager
    screenshot_service: ScreenshotService
    ocr_service: OCRService
    hotkey_manager: HotkeyManager
    automation_engine: AutomationEngine
    workflow_runner: WorkflowRunner
    task_scheduler: TaskScheduler
    application_manager: ApplicationManager

    @classmethod
    def build(cls) -> "WindowsIntegrationRuntime":
        security = OSSecurityPolicy()
        event_bus = EventBus()
        window_manager = WindowManager(security=security, event_bus=event_bus)
        screenshot_service = ScreenshotService(security=security, window_manager=window_manager)
        ocr_service = OCRService(security=security, screenshot_service=screenshot_service)
        hotkey_manager = HotkeyManager(event_bus=event_bus, security=security)
        automation_engine = AutomationEngine(
            security=security,
            window_manager=window_manager,
            screenshot_service=screenshot_service,
            ocr_service=ocr_service,
        )
        workflow_runner = WorkflowRunner(automation_engine, event_bus=event_bus)
        task_scheduler = TaskScheduler(workflow_runner, event_bus=event_bus)
        application_manager = ApplicationManager()
        return cls(
            security=security,
            event_bus=event_bus,
            window_manager=window_manager,
            screenshot_service=screenshot_service,
            ocr_service=ocr_service,
            hotkey_manager=hotkey_manager,
            automation_engine=automation_engine,
            workflow_runner=workflow_runner,
            task_scheduler=task_scheduler,
            application_manager=application_manager,
        )

    @property
    def workflow_executor(self) -> WorkflowRunner:
        return self.workflow_runner

    async def start(self) -> None:
        await self.event_bus.start()
        await self.task_scheduler.start()
        await self.window_manager.start_focus_monitor()

    async def stop(self) -> None:
        self.hotkey_manager.close()
        await self.window_manager.stop_focus_monitor()
        await self.task_scheduler.stop()
        await self.event_bus.stop()
