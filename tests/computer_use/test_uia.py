from types import SimpleNamespace

import pytest

from src.computer_use.models import UIControl
from src.computer_use.observer.uia import UIAutomationService


class FakeNode:
    def __init__(
        self,
        name,
        control_type,
        *,
        automation_id="",
        class_name="",
        children=(),
        fail_children=False,
    ):
        self.Name = name
        self.ControlTypeName = control_type
        self.AutomationId = automation_id
        self.ClassName = class_name
        self._children = tuple(children)
        self._fail_children = fail_children

    def GetChildren(self):
        if self._fail_children:
            raise RuntimeError("broken node")
        return self._children


def _service_with_root(root):
    service = UIAutomationService()
    service._uiautomation = SimpleNamespace(
        GetRootControl=lambda: root,
        ControlFromHandle=lambda handle: root,
    )
    service._pywinauto = None
    return service


def test_read_control_tree_redacts_sensitive_nodes_and_respects_limit():
    root = FakeNode(
        "Form",
        "Window",
        children=(
            FakeNode("API token", "Edit", automation_id="token"),
            FakeNode("Guardar", "Button", automation_id="save"),
        ),
    )
    service = _service_with_root(root)

    controls = service.read_control_tree(window_handle=99, limit=2)

    assert len(controls) == 2
    assert controls[1].name == "[sensitive]"
    assert controls[1].is_password is True
    assert all(control.name != "API token" for control in controls)


def test_read_control_tree_returns_partial_safe_result_for_broken_node():
    service = _service_with_root(FakeNode("Editor", "Window", fail_children=True))
    service._foreground_handle = lambda: 0

    controls = service.read_control_tree()

    assert len(controls) == 1
    assert controls[0].name == "Editor"
    assert controls[0].metadata["path"] == []


def test_find_helpers_filter_by_query_and_control_type(monkeypatch):
    service = UIAutomationService()
    controls = (
        UIControl(name="Guardar", control_type="Button"),
        UIControl(name="Nombre", control_type="Edit"),
        UIControl(name="Archivo", control_type="MenuItem"),
    )
    monkeypatch.setattr(service, "read_control_tree", lambda **kwargs: controls)

    assert service.find_buttons(query="guardar") == (controls[0],)
    assert service.find_inputs() == (controls[1],)
    assert service.find_menu_items(query="archivo") == (controls[2],)
    assert service.find_control_by_name("missing") is None


@pytest.mark.parametrize("method_name", ["invoke_control", "set_text"])
def test_sensitive_control_actions_are_blocked_before_adapter_checks(method_name):
    service = UIAutomationService()
    service._uiautomation = object()
    control = UIControl(name="[sensitive]", control_type="Edit", is_password=True)
    args = (control, "secret") if method_name == "set_text" else (control,)

    with pytest.raises(PermissionError, match="credenciales"):
        getattr(service, method_name)(*args)


def test_non_sensitive_actions_fail_cleanly_when_uia_is_unavailable():
    service = UIAutomationService()
    service._uiautomation = None
    service._pywinauto = None

    with pytest.raises(RuntimeError, match="no esta disponible"):
        service.invoke_control(UIControl(name="Guardar", control_type="Button"))


def test_invoke_control_uses_invoke_pattern(monkeypatch):
    called = []
    pattern = SimpleNamespace(Invoke=lambda: called.append("invoke"))
    node = SimpleNamespace(GetInvokePattern=lambda: pattern)
    service = UIAutomationService()
    control = UIControl(
        name="Guardar",
        control_type="Button",
        automation_id="save",
        metadata={"window_handle": 10, "window_pid": 20, "window_title": "UAT"},
    )
    monkeypatch.setattr(service, "_resolve_for_action", lambda item: node)

    result = service.invoke_control(control)

    assert called == ["invoke"]
    assert result["ok"] is True
    assert result["method"] == "uia_invoke"
    assert "name" not in result


def test_set_text_uses_value_pattern_and_verifies_without_returning_text(monkeypatch):
    values = []

    class ValuePattern:
        Value = ""

        def SetValue(self, value):
            values.append(value)
            self.Value = value

    pattern = ValuePattern()
    node = SimpleNamespace(GetValuePattern=lambda: pattern)
    service = UIAutomationService()
    control = UIControl(
        name="Document",
        control_type="Document",
        metadata={"window_handle": 10, "window_pid": 20, "window_title": "UAT"},
    )
    monkeypatch.setattr(service, "_resolve_for_action", lambda item: node)

    result = service.set_text(control, "Computer Use UAT OK")

    assert values == ["Computer Use UAT OK"]
    assert result["ok"] is True
    assert result["verified"] is True
    assert "text" not in result


def test_action_is_cancelled_when_focus_changes(monkeypatch):
    service = UIAutomationService()
    control = UIControl(
        name="Guardar",
        control_type="Button",
        metadata={"window_handle": 10, "window_pid": 20, "window_title": "UAT"},
    )
    monkeypatch.setattr(
        service,
        "_window_identity",
        lambda handle: {"window_handle": 10, "window_pid": 20, "window_title": "UAT"},
    )
    monkeypatch.setattr(service, "_foreground_handle", lambda: 11)

    with pytest.raises(RuntimeError, match="foco cambio"):
        service._assert_window_identity(control, require_foreground=True)


def test_action_is_cancelled_when_window_identity_changes(monkeypatch):
    service = UIAutomationService()
    control = UIControl(
        name="Guardar",
        control_type="Button",
        metadata={"window_handle": 10, "window_pid": 20, "window_title": "UAT"},
    )
    monkeypatch.setattr(
        service,
        "_window_identity",
        lambda handle: {"window_handle": 10, "window_pid": 99, "window_title": "UAT"},
    )

    with pytest.raises(RuntimeError, match="identidad"):
        service._assert_window_identity(control, require_foreground=False)


def test_alias_search_matches_spanish_and_english(monkeypatch):
    service = UIAutomationService()
    control = UIControl(name="Save", control_type="MenuItem")
    monkeypatch.setattr(service, "read_control_tree", lambda **kwargs: (control,))

    assert service.find_control_by_name("Guardar") == control


def test_invoke_named_control_expands_file_menu_only_for_confirmed_action(monkeypatch):
    service = UIAutomationService()
    file_menu = UIControl(name="File", control_type="MenuItem")
    save = UIControl(name="Save", control_type="MenuItem")
    searches = []
    invoked = []

    def find(name, **kwargs):
        searches.append(name)
        if name == "Archivo":
            return file_menu
        return save if invoked else None

    monkeypatch.setattr(service, "find_control_by_name", find)
    monkeypatch.setattr(service, "invoke_control", lambda control: invoked.append(control) or {"ok": True})
    monkeypatch.setattr("src.computer_use.observer.uia.time.sleep", lambda _: None)

    result = service.invoke_named_control("Guardar", window_handle=10)

    assert result["ok"] is True
    assert invoked == [file_menu, save]
    assert searches == ["Guardar", "Archivo", "Guardar"]
