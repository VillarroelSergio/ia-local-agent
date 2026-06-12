"""Optional UI Automation layer.

The service is dependency-optional: if pywinauto/uiautomation are not installed
the methods return empty results or controlled errors. This keeps the project
local-first without making UIA packages mandatory for API startup.
"""

from __future__ import annotations

from typing import Any

try:
    from computer_use.models import UIControl
except ModuleNotFoundError:
    from src.computer_use.models import UIControl


PASSWORD_CONTROL_TYPES = {"PasswordBox", "Edit"}
PASSWORD_NAME_HINTS = ("password", "contraseña", "passkey", "secret", "token")


class UIAutomationService:
    def __init__(self):
        self._uiautomation = self._optional_import("uiautomation")
        self._pywinauto = self._optional_import("pywinauto")

    @property
    def available(self) -> bool:
        return self._uiautomation is not None or self._pywinauto is not None

    def find_controls(self, *, window_handle: int | None = None, query: str | None = None, limit: int = 100) -> tuple[UIControl, ...]:
        controls = self.read_control_tree(window_handle=window_handle, limit=limit)
        if not query:
            return controls
        needle = query.lower()
        return tuple(
            control for control in controls
            if needle in " ".join(
                part for part in (control.name, control.control_type, control.automation_id, control.class_name) if part
            ).lower()
        )

    def find_buttons(self, *, window_handle: int | None = None, query: str | None = None) -> tuple[UIControl, ...]:
        return tuple(
            control for control in self.find_controls(window_handle=window_handle, query=query)
            if "button" in control.control_type.lower()
        )

    def find_inputs(self, *, window_handle: int | None = None, query: str | None = None) -> tuple[UIControl, ...]:
        return tuple(
            control for control in self.find_controls(window_handle=window_handle, query=query)
            if any(kind in control.control_type.lower() for kind in ("edit", "input", "textbox"))
        )

    def find_menu_items(self, *, window_handle: int | None = None, query: str | None = None) -> tuple[UIControl, ...]:
        return tuple(
            control for control in self.find_controls(window_handle=window_handle, query=query)
            if "menu" in control.control_type.lower()
        )

    def find_control_by_name(self, name: str, *, window_handle: int | None = None) -> UIControl | None:
        matches = self.find_controls(window_handle=window_handle, query=name, limit=20)
        return matches[0] if matches else None

    def invoke_control(self, control: UIControl) -> dict[str, Any]:
        if control.is_password:
            raise PermissionError("No se permite invocar controles de credenciales.")
        if not self.available:
            raise RuntimeError("UI Automation no esta disponible.")
        raise NotImplementedError("Invocacion UIA pendiente de adaptador especifico.")

    def set_text(self, control: UIControl, text: str) -> dict[str, Any]:
        if control.is_password:
            raise PermissionError("No se permite escribir en controles de credenciales.")
        if not self.available:
            raise RuntimeError("UI Automation no esta disponible.")
        raise NotImplementedError("Escritura UIA pendiente de adaptador especifico.")

    def read_control_tree(self, *, window_handle: int | None = None, limit: int = 100) -> tuple[UIControl, ...]:
        if self._uiautomation is None:
            return ()
        try:
            root = self._uiautomation.ControlFromHandle(window_handle) if window_handle else self._uiautomation.GetRootControl()
            controls: list[UIControl] = []
            self._walk_uiautomation(root, controls, limit)
            return tuple(controls)
        except Exception:
            return ()

    def _walk_uiautomation(self, node, controls: list[UIControl], limit: int) -> None:
        if len(controls) >= limit:
            return
        try:
            name = str(getattr(node, "Name", "") or "")
            control_type = str(getattr(node, "ControlTypeName", "") or getattr(node, "ControlType", "") or "")
            automation_id = str(getattr(node, "AutomationId", "") or "") or None
            class_name = str(getattr(node, "ClassName", "") or "") or None
            is_password = self._looks_sensitive(name, control_type)
            controls.append(UIControl(
                name="[sensitive]" if is_password else name,
                control_type=control_type,
                automation_id=automation_id,
                class_name=class_name,
                is_password=is_password,
            ))
            for child in node.GetChildren():
                self._walk_uiautomation(child, controls, limit)
                if len(controls) >= limit:
                    break
        except Exception:
            return

    def _looks_sensitive(self, name: str, control_type: str) -> bool:
        lowered = f"{name} {control_type}".lower()
        return any(hint in lowered for hint in PASSWORD_NAME_HINTS)

    def _optional_import(self, module_name: str):
        try:
            return __import__(module_name)
        except ImportError:
            return None
