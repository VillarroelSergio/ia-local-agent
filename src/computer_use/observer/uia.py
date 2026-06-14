"""Safe UI Automation observation and semantic actions."""

from __future__ import annotations

import ctypes
import time
import unicodedata
from typing import Any

try:
    from computer_use.models import UIControl
except ModuleNotFoundError:
    from src.computer_use.models import UIControl


PASSWORD_NAME_HINTS = ("password", "contrasena", "passkey", "secret", "token", "credential", "credencial")
SENSITIVE_WINDOW_HINTS = ("password", "contrasena", "login", "bank", "banco", "bitwarden", "keepass", "1password")
CONTROL_ALIASES = {
    "guardar": ("guardar", "save"),
    "archivo": ("archivo", "file"),
    "editar": ("editar", "edit"),
    "cerrar": ("cerrar", "close"),
    "aceptar": ("aceptar", "ok", "accept"),
    "cancelar": ("cancelar", "cancel"),
    "documento": ("documento", "editor", "text editor"),
}


class UIAutomationService:
    def __init__(self):
        self._uiautomation = self._optional_import("uiautomation")
        self._pywinauto = self._optional_import("pywinauto")

    @property
    def available(self) -> bool:
        return self._uiautomation is not None or self._pywinauto is not None

    def find_controls(
        self,
        *,
        window_handle: int | None = None,
        query: str | None = None,
        limit: int = 100,
    ) -> tuple[UIControl, ...]:
        controls = self.read_control_tree(window_handle=window_handle, limit=limit)
        if not query:
            return controls
        needles = self._query_variants(query)
        return tuple(
            control
            for control in controls
            if any(
                needle
                in self._normalize(
                    " ".join(
                        part
                        for part in (
                            control.name,
                            control.control_type,
                            control.automation_id,
                            control.class_name,
                        )
                        if part
                    )
                )
                for needle in needles
            )
        )

    def find_buttons(self, *, window_handle: int | None = None, query: str | None = None) -> tuple[UIControl, ...]:
        return tuple(
            control
            for control in self.find_controls(window_handle=window_handle, query=query)
            if "button" in control.control_type.lower()
        )

    def find_inputs(self, *, window_handle: int | None = None, query: str | None = None) -> tuple[UIControl, ...]:
        controls = self.find_controls(window_handle=window_handle, query=query)
        return tuple(
            control
            for control in controls
            if any(kind in control.control_type.lower() for kind in ("edit", "input", "textbox", "document"))
        )

    def find_menu_items(self, *, window_handle: int | None = None, query: str | None = None) -> tuple[UIControl, ...]:
        return tuple(
            control
            for control in self.find_controls(window_handle=window_handle, query=query)
            if "menu" in control.control_type.lower()
        )

    def find_control_by_name(self, name: str, *, window_handle: int | None = None) -> UIControl | None:
        matches = self.find_controls(window_handle=window_handle, query=name, limit=200)
        return matches[0] if matches else None

    def invoke_control(self, control: UIControl) -> dict[str, Any]:
        node = self._resolve_for_action(control)
        for pattern_name, method_name in (
            ("GetInvokePattern", "Invoke"),
            ("GetSelectionItemPattern", "Select"),
            ("GetTogglePattern", "Toggle"),
        ):
            pattern = self._pattern(node, pattern_name)
            if pattern is not None:
                getattr(pattern, method_name)()
                return self._action_result(control, f"uia_{method_name.lower()}")
        click = getattr(node, "Click", None)
        if callable(click):
            click(simulateMove=False)
            return self._action_result(control, "uia_click")
        raise RuntimeError("El control no expone un patron UIA invocable.")

    def invoke_named_control(self, query: str, *, window_handle: int | None = None) -> dict[str, Any]:
        control = self.find_control_by_name(query, window_handle=window_handle)
        if control is None and "save" in self._query_variants(query):
            menu = self.find_control_by_name("Archivo", window_handle=window_handle)
            if menu is not None:
                self.invoke_control(menu)
                time.sleep(0.15)
                control = self.find_control_by_name(query, window_handle=window_handle)
        if control is None:
            raise ValueError("Control UIA no encontrado.")
        return self.invoke_control(control)

    def set_text(self, control: UIControl, text: str) -> dict[str, Any]:
        if not isinstance(text, str) or not text:
            raise ValueError("El texto no puede estar vacio.")
        node = self._resolve_for_action(control)
        value_pattern = self._pattern(node, "GetValuePattern")
        if value_pattern is not None:
            value_pattern.SetValue(text)
            result = self._action_result(control, "uia_set_value")
        else:
            set_focus = getattr(node, "SetFocus", None)
            send_keys = getattr(node, "SendKeys", None)
            if not callable(set_focus) or not callable(send_keys):
                raise RuntimeError("El control no expone un patron UIA de escritura.")
            set_focus()
            self._assert_window_identity(control, require_foreground=True)
            send_keys(text, waitTime=0.01)
            result = self._action_result(control, "uia_send_keys")
        value = self._read_value(node)
        result["verified"] = bool(value and text in value)
        result["ok"] = result["verified"]
        return result

    def read_control_tree(self, *, window_handle: int | None = None, limit: int = 100) -> tuple[UIControl, ...]:
        if self._uiautomation is None:
            return ()
        try:
            handle = window_handle or self._foreground_handle()
            root = (
                self._uiautomation.ControlFromHandle(handle)
                if handle
                else self._uiautomation.GetRootControl()
            )
            handle = handle or self._native_handle(root)
            identity = self._window_identity(handle)
            controls: list[UIControl] = []
            self._walk_uiautomation(root, controls, limit, path=(), identity=identity)
            return tuple(controls)
        except Exception:
            return ()

    def _walk_uiautomation(
        self,
        node,
        controls: list[UIControl],
        limit: int,
        *,
        path: tuple[int, ...],
        identity: dict[str, Any],
    ) -> None:
        if len(controls) >= limit:
            return
        try:
            name = str(getattr(node, "Name", "") or "")
            control_type = str(getattr(node, "ControlTypeName", "") or getattr(node, "ControlType", "") or "")
            automation_id = str(getattr(node, "AutomationId", "") or "") or None
            class_name = str(getattr(node, "ClassName", "") or "") or None
            is_password = self._looks_sensitive(name, control_type)
            controls.append(
                UIControl(
                    name="[sensitive]" if is_password else name,
                    control_type=control_type,
                    automation_id=automation_id,
                    class_name=class_name,
                    value=None if is_password else self._read_value(node),
                    is_password=is_password,
                    metadata={**identity, "path": list(path)},
                )
            )
            for index, child in enumerate(node.GetChildren()):
                self._walk_uiautomation(
                    child,
                    controls,
                    limit,
                    path=path + (index,),
                    identity=identity,
                )
                if len(controls) >= limit:
                    break
        except Exception:
            return

    def _resolve_for_action(self, control: UIControl):
        if control.is_password or self._looks_sensitive(control.name, control.control_type):
            raise PermissionError("No se permite actuar sobre controles de credenciales.")
        if not self.available or self._uiautomation is None:
            raise RuntimeError("UI Automation no esta disponible.")
        self._assert_window_identity(control, require_foreground=True)
        handle = int(control.metadata.get("window_handle") or 0)
        node = self._uiautomation.ControlFromHandle(handle)
        for index in control.metadata.get("path", []):
            children = node.GetChildren()
            if index < 0 or index >= len(children):
                raise RuntimeError("El control UIA ya no existe en la ventana objetivo.")
            node = children[index]
        if control.automation_id and str(getattr(node, "AutomationId", "") or "") != control.automation_id:
            raise RuntimeError("La identidad del control UIA cambio antes de actuar.")
        if control.class_name and str(getattr(node, "ClassName", "") or "") != control.class_name:
            raise RuntimeError("La identidad del control UIA cambio antes de actuar.")
        if self._looks_sensitive(
            str(getattr(node, "Name", "") or ""),
            str(getattr(node, "ControlTypeName", "") or ""),
        ):
            raise PermissionError("No se permite actuar sobre controles de credenciales.")
        return node

    def _assert_window_identity(self, control: UIControl, *, require_foreground: bool) -> None:
        expected_handle = int(control.metadata.get("window_handle") or 0)
        expected_pid = int(control.metadata.get("window_pid") or 0)
        expected_title = str(control.metadata.get("window_title") or "")
        if not expected_handle:
            raise RuntimeError("El control no incluye una ventana objetivo verificable.")
        actual = self._window_identity(expected_handle)
        if actual["window_handle"] != expected_handle or (
            expected_pid and actual["window_pid"] != expected_pid
        ):
            raise RuntimeError("La identidad de la ventana cambio antes de actuar.")
        if expected_title and actual["window_title"] != expected_title:
            raise RuntimeError("El titulo de la ventana cambio antes de actuar.")
        if self._looks_sensitive_window(actual["window_title"]):
            raise PermissionError("La ventana objetivo es sensible.")
        if require_foreground and self._foreground_handle() != expected_handle:
            raise RuntimeError("El foco cambio antes de actuar; accion cancelada.")

    @staticmethod
    def _pattern(node, method_name: str):
        method = getattr(node, method_name, None)
        if not callable(method):
            return None
        try:
            return method()
        except Exception:
            return None

    def _read_value(self, node) -> str:
        pattern = self._pattern(node, "GetValuePattern")
        if pattern is None:
            return ""
        try:
            return str(getattr(pattern, "Value", "") or "")
        except Exception:
            return ""

    @staticmethod
    def _action_result(control: UIControl, method: str) -> dict[str, Any]:
        return {
            "ok": True,
            "method": method,
            "window_handle": control.metadata.get("window_handle"),
            "window_pid": control.metadata.get("window_pid"),
            "control_type": control.control_type,
            "automation_id": control.automation_id,
        }

    def _window_identity(self, handle: int) -> dict[str, Any]:
        if not handle:
            return {"window_handle": 0, "window_pid": 0, "window_title": ""}
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(ctypes.c_void_p(handle), ctypes.byref(pid))
        length = ctypes.windll.user32.GetWindowTextLengthW(ctypes.c_void_p(handle))
        buffer = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(ctypes.c_void_p(handle), buffer, length + 1)
        return {
            "window_handle": int(handle),
            "window_pid": int(pid.value),
            "window_title": buffer.value,
        }

    @staticmethod
    def _native_handle(node) -> int:
        return int(getattr(node, "NativeWindowHandle", 0) or 0)

    @staticmethod
    def _foreground_handle() -> int:
        return int(ctypes.windll.user32.GetForegroundWindow() or 0)

    def _looks_sensitive_window(self, title: str) -> bool:
        normalized = self._normalize(title)
        return any(hint in normalized for hint in SENSITIVE_WINDOW_HINTS)

    def _looks_sensitive(self, name: str, control_type: str) -> bool:
        normalized = self._normalize(f"{name} {control_type}")
        return any(hint in normalized for hint in PASSWORD_NAME_HINTS)

    def _query_variants(self, query: str) -> tuple[str, ...]:
        normalized = self._normalize(query)
        return tuple(dict.fromkeys((normalized, *CONTROL_ALIASES.get(normalized, ()))))

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "")
        return "".join(char for char in normalized if not unicodedata.combining(char)).lower().strip()

    @staticmethod
    def _optional_import(module_name: str):
        try:
            return __import__(module_name)
        except ImportError:
            return None
