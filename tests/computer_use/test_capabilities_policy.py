import asyncio
from types import SimpleNamespace

import pytest

from src.computer_use.capabilities import (
    ConfirmationStore,
    HIGH_RISK_CAPABILITIES,
    SEMANTIC_CAPABILITIES,
    is_high_risk,
)
from src.computer_use.executor import ComputerUseExecutor
from src.computer_use.models import Plan, PlanStep
from src.os_integration.automation import StepResult
from src.os_integration.models import WindowInfo
from src.os_integration.security import OSDecision, OSScope, OSSecurityPolicy


def _window(title="Editor", process_name="code.exe"):
    return WindowInfo(
        handle=1,
        title=title,
        process_name=process_name,
        pid=2,
        rect=None,
        monitor_index=0,
    )


class FakeSecurity:
    def __init__(self, decision):
        self.decision = decision
        self.calls = []

    def evaluate_scope(self, scope, window):
        self.calls.append((scope, window))
        return self.decision


class FakeRunner:
    def __init__(self, *, result=None, window=None):
        self.engine = SimpleNamespace(
            security=None,
            window_manager=SimpleNamespace(get_active_window=lambda: window or _window()),
        )
        self.result = result or StepResult("step", True, result={"ok": True})
        self.workflows = []

    async def run(self, workflow):
        self.workflows.append(workflow)
        return [self.result]


def test_capability_registry_has_unique_semantic_names_and_risk_subset():
    assert len(SEMANTIC_CAPABILITIES) == len(set(SEMANTIC_CAPABILITIES))
    assert HIGH_RISK_CAPABILITIES < set(SEMANTIC_CAPABILITIES)
    assert all(is_high_risk(name) for name in HIGH_RISK_CAPABILITIES)
    assert not is_high_risk("extract_visible_text")
    assert not is_high_risk("unknown")


@pytest.mark.parametrize(
    ("capability", "expected_scope"),
    [
        ("focus_window", OSScope.WINDOW_CONTROL),
        ("organize_windows", OSScope.WINDOW_CONTROL),
        ("extract_visible_text", OSScope.WINDOW_INSPECT),
        ("run_safe_workflow", OSScope.WINDOW_INSPECT),
        ("click_ui_control", OSScope.MOUSE_INPUT),
        ("fill_text_field", OSScope.KEYBOARD_INPUT),
    ],
)
def test_executor_maps_capabilities_to_policy_scope(capability, expected_scope):
    security = FakeSecurity(OSDecision(True, "allowed"))
    confirmations = ConfirmationStore()
    executor = ComputerUseExecutor(
        FakeRunner(),
        security=security,
        confirmations=confirmations,
    )
    token = None
    if is_high_risk(capability):
        token = confirmations.issue("session-1", capability).token

    decision = executor._evaluate_capability(
        PlanStep(capability, "step"),
        session_id="session-1",
        confirmation_token=token,
    )

    assert security.calls[0][0] is expected_scope
    assert decision["allowed"] is True
    assert decision["requires_confirmation"] is is_high_risk(capability)


def test_executor_does_not_run_workflow_when_policy_denies():
    runner = FakeRunner()
    security = FakeSecurity(OSDecision(False, "sensitive window", True))
    executor = ComputerUseExecutor(runner, security=security)

    result = asyncio.run(executor.execute_step(PlanStep("focus_window", "focus")))

    assert result["ok"] is False
    assert result["error"] == "sensitive window"
    assert runner.workflows == []


def test_focus_workflow_consumes_confirmation_before_execution():
    runner = FakeRunner()
    confirmations = ConfirmationStore()
    executor = ComputerUseExecutor(
        runner,
        security=FakeSecurity(OSDecision(True, "allowed", False)),
        confirmations=confirmations,
    )
    token = confirmations.issue("session-1", "focus_window").token

    result = asyncio.run(
        executor.execute_step(
            PlanStep("focus_window", "focus", args={"query": "Editor"}),
            session_id="session-1",
            confirmation_token=token,
        )
    )

    assert result["ok"] is True
    workflow = runner.workflows[0]
    assert workflow.steps[0].action == "focus_window"
    assert workflow.steps[0].require_confirmation is False
    assert workflow.metadata["capability"] == "focus_window"


def test_execute_plan_stops_after_first_failed_step():
    runner = FakeRunner(result=StepResult("step", False, error="failed"))
    confirmations = ConfirmationStore()
    executor = ComputerUseExecutor(
        runner,
        security=FakeSecurity(OSDecision(True, "allowed")),
        confirmations=confirmations,
    )
    plan = Plan(
        goal="goal",
        steps=(
            PlanStep("run_safe_workflow", "first"),
            PlanStep("run_safe_workflow", "second"),
        ),
    )

    first_token = confirmations.issue("session-1", "run_safe_workflow").token
    result = asyncio.run(
        executor.execute_plan(
            plan,
            session_id="session-1",
            confirmation_tokens={plan.steps[0].id: first_token},
        )
    )

    assert result["ok"] is False
    assert len(result["results"]) == 1
    assert len(runner.workflows) == 1


def test_uia_action_requires_confirmation_before_adapter_call():
    runner = FakeRunner()
    service = SimpleNamespace(
        find_controls=lambda **kwargs: (_ for _ in ()).throw(AssertionError("adapter called")),
    )
    executor = ComputerUseExecutor(
        runner,
        security=FakeSecurity(OSDecision(True, "allowed")),
        confirmations=ConfirmationStore(),
        ui_automation=service,
    )

    result = asyncio.run(executor.execute_step(
        PlanStep("click_ui_control", "click", args={"name": "Guardar"}),
        session_id="session-1",
    ))

    assert result["ok"] is False
    assert result["error"] == "computer_use_confirmation_required"


def test_confirmation_grant_is_bound_to_session_capability_and_single_use():
    confirmations = ConfirmationStore()
    grant = confirmations.issue("session-1", "focus_window")

    assert confirmations.consume(
        grant.token,
        session_id="wrong-session",
        capability="focus_window",
    ) is False
    assert confirmations.consume(
        grant.token,
        session_id="session-1",
        capability="focus_window",
    ) is False

    valid = confirmations.issue("session-1", "focus_window")
    assert confirmations.consume(
        valid.token,
        session_id="session-1",
        capability="focus_window",
    ) is True
    assert confirmations.consume(
        valid.token,
        session_id="session-1",
        capability="focus_window",
    ) is False


def test_os_policy_blocks_sensitive_processes_and_titles():
    policy = OSSecurityPolicy()

    assert policy.evaluate_scope(OSScope.WINDOW_INSPECT, _window(process_name="Bitwarden.exe")).allowed is False
    assert policy.evaluate_scope(OSScope.WINDOW_INSPECT, _window(title="API token")).allowed is False


def test_os_policy_requires_confirmation_for_window_control():
    decision = OSSecurityPolicy().evaluate_scope(OSScope.WINDOW_CONTROL, _window())

    assert decision.allowed is True
    assert decision.requires_confirmation is True
