"""Desktop observer with native-first source priority."""

from __future__ import annotations

from dataclasses import asdict

try:
    from computer_use.models import DesktopObservation, ObservationSource
    from computer_use.observer.uia import UIAutomationService
    from computer_use.observer.vision import NullVisionProvider, VisionProvider
    from os_integration.models import CaptureTarget, ScreenshotRequest
    from os_integration.ocr import OCRService
    from os_integration.security import OSScope, OSSecurityPolicy
    from os_integration.windows import WindowManager
except ModuleNotFoundError:
    from src.computer_use.models import DesktopObservation, ObservationSource
    from src.computer_use.observer.uia import UIAutomationService
    from src.computer_use.observer.vision import NullVisionProvider, VisionProvider
    from src.os_integration.models import CaptureTarget, ScreenshotRequest
    from src.os_integration.ocr import OCRService
    from src.os_integration.security import OSScope, OSSecurityPolicy
    from src.os_integration.windows import WindowManager


class DesktopObserver:
    def __init__(
        self,
        *,
        window_manager: WindowManager | None = None,
        ui_automation: UIAutomationService | None = None,
        ocr_service: OCRService | None = None,
        vision_provider: VisionProvider | None = None,
        security: OSSecurityPolicy | None = None,
    ):
        self.security = security or OSSecurityPolicy()
        self.window_manager = window_manager or WindowManager(security=self.security)
        self.ui_automation = ui_automation or UIAutomationService()
        self.ocr_service = ocr_service or OCRService(security=self.security)
        self.vision_provider = vision_provider or NullVisionProvider()

    def observe_desktop(self, *, include_ocr: bool = False) -> DesktopObservation:
        active_window = self.window_manager.get_active_window()
        decision = self.security.evaluate_scope(OSScope.WINDOW_INSPECT, active_window)
        if not decision.allowed:
            return self._blocked_observation(decision.reason)
        open_windows = self.window_manager.list_windows(limit=100)
        controls = self._read_controls(active_window.handle if active_window else None)
        visible_text = self._controls_text(controls)
        used_sources = [ObservationSource.WINDOW_MANAGER]
        if controls:
            used_sources.append(ObservationSource.UI_AUTOMATION)
        if include_ocr and not visible_text:
            visible_text = self.extract_visible_text()
            if visible_text:
                used_sources.append(ObservationSource.OCR)
        return self.generate_observation(
            active_window=active_window,
            open_windows=open_windows,
            controls=controls,
            visible_text=visible_text,
            used_sources=tuple(used_sources),
        )

    def observe_window(self, handle: int | None = None, *, include_ocr: bool = False) -> DesktopObservation:
        window = self.window_manager.get_window_info(handle) if handle else self.window_manager.get_active_window()
        decision = self.security.evaluate_scope(OSScope.WINDOW_INSPECT, window)
        if not decision.allowed:
            return self._blocked_observation(decision.reason)
        controls = self._read_controls(window.handle if window else None)
        visible_text = self._controls_text(controls)
        used_sources = [ObservationSource.WINDOW_MANAGER]
        if controls:
            used_sources.append(ObservationSource.UI_AUTOMATION)
        if include_ocr and not visible_text:
            visible_text = self.extract_visible_text(window_handle=window.handle if window else None)
            if visible_text:
                used_sources.append(ObservationSource.OCR)
        return self.generate_observation(
            active_window=window,
            open_windows=(window,) if window else (),
            controls=controls,
            visible_text=visible_text,
            used_sources=tuple(used_sources),
        )

    def observe_application(self, query: str, *, include_ocr: bool = False) -> DesktopObservation:
        matches = self.window_manager.find_windows(query, limit=1)
        return self.observe_window(matches[0].handle if matches else None, include_ocr=include_ocr)

    def extract_visible_text(self, *, window_handle: int | None = None, language: str = "eng") -> str:
        request = ScreenshotRequest(target=CaptureTarget.ACTIVE_WINDOW, window_handle=window_handle)
        result = self.ocr_service.read_screen(request, language=language)
        return result.text

    def generate_observation(
        self,
        *,
        active_window,
        open_windows,
        controls,
        visible_text: str,
        used_sources: tuple[ObservationSource, ...],
    ) -> DesktopObservation:
        window_summary = ""
        if active_window:
            window_summary = f"{active_window.title} ({active_window.process_name or 'unknown'})"
        return DesktopObservation(
            active_window=active_window,
            open_windows=tuple(open_windows),
            controls=tuple(controls),
            visible_text=visible_text,
            screen_summary=window_summary,
            source_order=(
                ObservationSource.WINDOW_MANAGER,
                ObservationSource.UI_AUTOMATION,
                ObservationSource.OCR,
                ObservationSource.VISION,
            ),
            used_sources=used_sources,
            metadata={
                "active_window": asdict(active_window) if active_window else None,
                "ui_automation_available": self.ui_automation.available,
                "vision_provider": self.vision_provider.name,
            },
            confidence=0.9 if controls else 0.65,
            limitations=() if controls else ("UI Automation no devolvio controles.",),
        )

    def _blocked_observation(self, reason: str) -> DesktopObservation:
        return DesktopObservation(
            active_window=None,
            open_windows=(),
            controls=(),
            visible_text="",
            screen_summary="Ventana sensible bloqueada por politica.",
            source_order=(ObservationSource.WINDOW_MANAGER,),
            used_sources=(ObservationSource.WINDOW_MANAGER,),
            metadata={"policy": "blocked"},
            confidence=1.0,
            limitations=(reason,),
            sensitive_content_detected=True,
            blocked_by_policy=True,
        )

    def _read_controls(self, window_handle: int | None):
        return self.ui_automation.read_control_tree(window_handle=window_handle, limit=120)

    def _controls_text(self, controls) -> str:
        parts = []
        for control in controls:
            if control.is_password:
                continue
            if control.name:
                parts.append(control.name)
            if control.value:
                parts.append(control.value)
        return "\n".join(dict.fromkeys(parts))
