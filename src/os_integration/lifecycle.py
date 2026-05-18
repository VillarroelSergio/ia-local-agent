"""Lifecycle manager wiring Windows integration services together."""

from __future__ import annotations

from dataclasses import dataclass

from .automation import AutomationEngine, WorkflowExecutor
from .events import EventBus
from .hotkeys import HotkeyManager
from .ocr import OCRService
from .screenshots import ScreenshotService
from .security import OSSecurityPolicy
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
    workflow_executor: WorkflowExecutor

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
        workflow_executor = WorkflowExecutor(automation_engine, event_bus=event_bus)
        return cls(
            security=security,
            event_bus=event_bus,
            window_manager=window_manager,
            screenshot_service=screenshot_service,
            ocr_service=ocr_service,
            hotkey_manager=hotkey_manager,
            automation_engine=automation_engine,
            workflow_executor=workflow_executor,
        )

    async def start(self) -> None:
        await self.event_bus.start()
        await self.window_manager.start_focus_monitor()

    async def stop(self) -> None:
        self.hotkey_manager.close()
        await self.window_manager.stop_focus_monitor()
        await self.event_bus.stop()
