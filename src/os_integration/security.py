"""OS-level permission policy for desktop automation."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum

from .models import WindowInfo


class OSScope(str, Enum):
    SCREEN_CAPTURE = "screen.capture"
    OCR_READ = "ocr.read"
    WINDOW_INSPECT = "window.inspect"
    WINDOW_CONTROL = "window.control"
    KEYBOARD_INPUT = "keyboard.input"
    MOUSE_INPUT = "mouse.input"
    CLIPBOARD_READ = "clipboard.read"
    HOTKEY_REGISTER = "hotkey.register"
    SYSTEM_EVENT_READ = "system_event.read"


class TrustLevel(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    TRUSTED = "trusted"


@dataclass(frozen=True)
class OSDecision:
    allowed: bool
    reason: str
    requires_confirmation: bool = False


@dataclass
class OSSecurityPolicy:
    """Conservative desktop security policy.

    This complements tool permissions with app/window-aware checks. The
    defaults intentionally block credential managers, admin surfaces and
    browser/private profile internals unless the user explicitly extends the
    policy.
    """

    allowed_scopes: set[OSScope] = field(default_factory=lambda: {
        OSScope.SCREEN_CAPTURE,
        OSScope.OCR_READ,
        OSScope.WINDOW_INSPECT,
        OSScope.HOTKEY_REGISTER,
        OSScope.SYSTEM_EVENT_READ,
    })
    confirm_scopes: set[OSScope] = field(default_factory=lambda: {
        OSScope.KEYBOARD_INPUT,
        OSScope.MOUSE_INPUT,
        OSScope.WINDOW_CONTROL,
        OSScope.CLIPBOARD_READ,
    })
    denied_process_patterns: tuple[str, ...] = (
        "*keepass*",
        "*1password*",
        "*bitwarden*",
        "*lastpass*",
        "*credential*",
        "*login*",
        "*authenticator*",
        "lusrmgr.exe",
        "regedit.exe",
        "powershell_ise.exe",
    )
    denied_title_patterns: tuple[str, ...] = (
        "*password*",
        "*contraseña*",
        "*passkey*",
        "*secret*",
        "*token*",
        "*private key*",
        "*administrator:*",
        "*administrador:*",
    )
    allowed_process_patterns: tuple[str, ...] = ()
    secure_mode: bool = True

    def evaluate_scope(self, scope: OSScope, window: WindowInfo | None = None) -> OSDecision:
        if scope not in self.allowed_scopes and scope not in self.confirm_scopes:
            return OSDecision(False, f"Scope no permitido: {scope.value}")

        window_decision = self.evaluate_window(window) if window else OSDecision(True, "Ventana permitida.")
        if not window_decision.allowed:
            return window_decision

        if scope in self.confirm_scopes:
            return OSDecision(True, f"Scope requiere confirmacion: {scope.value}", True)

        return OSDecision(True, "Permitido por politica OS.")

    def evaluate_window(self, window: WindowInfo | None) -> OSDecision:
        if window is None:
            return OSDecision(True, "Sin ventana objetivo.")

        process_name = (window.process_name or "").lower()
        title = (window.title or "").lower()

        if self.allowed_process_patterns and not any(
            fnmatch.fnmatch(process_name, pattern.lower())
            for pattern in self.allowed_process_patterns
        ):
            return OSDecision(False, f"Proceso fuera de allowlist OS: {process_name}")

        if any(fnmatch.fnmatch(process_name, pattern.lower()) for pattern in self.denied_process_patterns):
            return OSDecision(False, f"Proceso sensible bloqueado: {process_name}")

        if any(fnmatch.fnmatch(title, pattern.lower()) for pattern in self.denied_title_patterns):
            return OSDecision(False, "Titulo de ventana sensible bloqueado.")

        return OSDecision(True, "Ventana permitida.")
