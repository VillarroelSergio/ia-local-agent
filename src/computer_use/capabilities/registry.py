"""Capability registry and one-shot internal confirmations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from threading import RLock
from uuid import uuid4

try:
    from computer_use.models import utc_now
except ModuleNotFoundError:
    from src.computer_use.models import utc_now


@dataclass(frozen=True)
class Capability:
    name: str
    scope: str
    high_risk: bool = False
    requires_confirmation: bool = False


CAPABILITIES: dict[str, Capability] = {
    item.name: item for item in (
        Capability("observe_desktop", "window.inspect"),
        Capability("observe_active_window", "window.inspect"),
        Capability("focus_window", "window.control", True, True),
        Capability("summarize_active_window", "window.inspect"),
        Capability("extract_visible_text", "window.inspect"),
        Capability("find_ui_control", "window.inspect"),
        Capability("click_ui_control", "mouse.input", True, True),
        Capability("fill_text_field", "keyboard.input", True, True),
        Capability("organize_windows", "window.control", True, True),
        Capability("run_safe_workflow", "automation.compose", True, True),
    )
}
SEMANTIC_CAPABILITIES = tuple(CAPABILITIES)
HIGH_RISK_CAPABILITIES = frozenset(name for name, item in CAPABILITIES.items() if item.high_risk)


@dataclass(frozen=True)
class ConfirmationGrant:
    token: str
    session_id: str
    capability: str
    expires_at: object


class ConfirmationStore:
    """In-memory, short-lived and one-shot grants for internal execution."""

    def __init__(self, *, ttl_seconds: int = 300):
        self.ttl_seconds = max(1, ttl_seconds)
        self._grants: dict[str, ConfirmationGrant] = {}
        self._lock = RLock()

    def issue(self, session_id: str, capability: str) -> ConfirmationGrant:
        require_capability(capability)
        now = utc_now()
        grant = ConfirmationGrant(
            token=f"cu_confirm_{uuid4().hex}",
            session_id=session_id,
            capability=capability,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        with self._lock:
            self._grants[grant.token] = grant
        return grant

    def consume(self, token: str | None, *, session_id: str, capability: str) -> bool:
        if not token:
            return False
        with self._lock:
            grant = self._grants.pop(token, None)
        return bool(
            grant
            and grant.session_id == session_id
            and grant.capability == capability
            and grant.expires_at >= utc_now()
        )

    def revoke_session(self, session_id: str) -> None:
        with self._lock:
            self._grants = {
                token: grant for token, grant in self._grants.items()
                if grant.session_id != session_id
            }


def require_capability(capability: str) -> Capability:
    try:
        return CAPABILITIES[capability]
    except KeyError as error:
        raise ValueError(f"Capacidad no registrada: {capability}") from error


def is_high_risk(capability: str) -> bool:
    item = CAPABILITIES.get(capability)
    return bool(item and item.high_risk)
