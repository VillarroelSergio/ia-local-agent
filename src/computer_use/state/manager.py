"""State manager for current and previous observations."""

from __future__ import annotations

from dataclasses import dataclass

try:
    from computer_use.models import DesktopObservation
except ModuleNotFoundError:
    from src.computer_use.models import DesktopObservation


@dataclass
class ComputerStateManager:
    current_observation: DesktopObservation | None = None
    previous_observation: DesktopObservation | None = None
    current_workflow_id: str | None = None

    def update_observation(self, observation: DesktopObservation) -> dict:
        self.previous_observation = self.current_observation
        self.current_observation = observation
        return self.detect_changes()

    def detect_changes(self) -> dict:
        previous = self.previous_observation
        current = self.current_observation
        if previous is None or current is None:
            return {"changed": previous is not current}
        previous_handle = previous.active_window.handle if previous.active_window else None
        current_handle = current.active_window.handle if current.active_window else None
        return {
            "changed": previous_handle != current_handle or previous.visible_text != current.visible_text,
            "active_window_changed": previous_handle != current_handle,
            "visible_text_changed": previous.visible_text != current.visible_text,
        }

    @property
    def active_window(self):
        return self.current_observation.active_window if self.current_observation else None

    @property
    def current_app(self) -> str | None:
        window = self.active_window
        return window.process_name if window else None
