from types import SimpleNamespace

import pytest

from src.computer_use.models import ObservationSource, UIControl
from src.computer_use.observer import DesktopObserver
from src.os_integration.models import Rect, WindowInfo, WindowState
from src.os_integration.security import OSDecision


def _window(handle=7, title="Editor", process_name="code.exe"):
    return WindowInfo(
        handle=handle,
        title=title,
        process_name=process_name,
        pid=42,
        rect=Rect(0, 0, 800, 600),
        monitor_index=0,
        state=WindowState.NORMAL,
    )


class FakeWindowManager:
    def __init__(self, window=None):
        self.window = window or _window()

    def get_active_window(self):
        return self.window

    def get_window_info(self, handle):
        return self.window if handle == self.window.handle else None

    def list_windows(self, limit=100):
        return [self.window]

    def find_windows(self, query, limit=1):
        return [self.window] if query.lower() in self.window.title.lower() else []


class FakeUIA:
    available = True

    def __init__(self, controls=()):
        self.controls = tuple(controls)
        self.calls = []

    def read_control_tree(self, *, window_handle=None, limit=100):
        self.calls.append((window_handle, limit))
        return self.controls


class FakeOCR:
    def __init__(self, text):
        self.text = text
        self.requests = []

    def read_screen(self, request, *, language):
        self.requests.append((request, language))
        return SimpleNamespace(text=self.text)


class FakeSecurity:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def evaluate_scope(self, scope, window):
        return OSDecision(self.allowed, "allowed" if self.allowed else "blocked")


def _observer(*, controls=(), ocr_text="", security=None):
    return DesktopObserver(
        window_manager=FakeWindowManager(),
        ui_automation=FakeUIA(controls),
        ocr_service=FakeOCR(ocr_text),
        security=security or FakeSecurity(),
    )


def test_observe_desktop_prefers_uia_text_and_skips_ocr():
    controls = (
        UIControl(name="Guardar", control_type="Button", value="listo"),
        UIControl(name="Password", control_type="Edit", value="top-secret", is_password=True),
        UIControl(name="Guardar", control_type="Text"),
    )
    observer = _observer(controls=controls, ocr_text="OCR fallback")

    observation = observer.observe_desktop(include_ocr=True)

    assert observation.visible_text == "Guardar\nlisto"
    assert observation.used_sources == (
        ObservationSource.WINDOW_MANAGER,
        ObservationSource.UI_AUTOMATION,
    )
    assert observer.ocr_service.requests == []
    assert "top-secret" not in observation.visible_text


def test_observe_desktop_uses_ocr_only_when_uia_has_no_text():
    observer = _observer(ocr_text="texto desde OCR")

    observation = observer.observe_desktop(include_ocr=True)

    assert observation.visible_text == "texto desde OCR"
    assert observation.used_sources == (
        ObservationSource.WINDOW_MANAGER,
        ObservationSource.OCR,
    )
    request, language = observer.ocr_service.requests[0]
    assert request.window_handle is None
    assert language == "eng"


def test_observe_window_checks_policy_before_reading_controls():
    observer = _observer(security=FakeSecurity(allowed=False))

    observation = observer.observe_window(7)

    assert observation.blocked_by_policy is True
    assert observation.sensitive_content_detected is True
    assert observer.ui_automation.calls == []


def test_observe_application_falls_back_to_active_window_when_no_match():
    observer = _observer()

    observation = observer.observe_application("missing")

    assert observation.active_window.handle == 7
    assert observer.ui_automation.calls == [(7, 120)]
