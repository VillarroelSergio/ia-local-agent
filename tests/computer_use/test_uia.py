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

    assert service.read_control_tree() == (
        UIControl(name="Editor", control_type="Window"),
    )


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

