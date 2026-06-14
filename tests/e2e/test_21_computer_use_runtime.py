import asyncio

from src.computer_use import ComputerUseEngine
from src.computer_use.models import ComputerUseSession, ComputerUseStatus, DesktopObservation, PlanStep, UIControl
from src.computer_use.observer.uia import UIAutomationService
from src.computer_use.planner import ComputerUsePlanner
from src.computer_use.sessions import ComputerUseSessionStore
from src.computer_use.state import ComputerStateManager
from src.computer_use.verifier import ResultVerifier
from src.os_integration.events import EventType
from src.os_integration.lifecycle import WindowsIntegrationRuntime
from src.tools import build_tool_registry


def test_computer_use_tools_are_registered():
    registry = build_tool_registry()
    expected = {
        "computer_use",
        "observe_desktop",
        "observe_window",
        "find_ui_control",
        "click_ui_control",
        "fill_text_field",
        "execute_workflow",
        "analyze_application",
        "automate_application",
    }

    assert expected.issubset(set(registry.names()))
    orchestrator = registry.require("computer_use").metadata
    assert orchestrator.requires_confirmation is False
    assert orchestrator.risk_level.value == "safe"
    assert registry.require("observe_desktop").metadata.risk_level.value == "read_only"


def test_computer_use_events_exist():
    assert EventType.COMPUTER_USE_STARTED.value == "computer_use.started"
    assert EventType.COMPUTER_USE_COMPLETED.value == "computer_use.completed"


def test_session_store_roundtrip(sandbox):
    store = ComputerUseSessionStore(sandbox / "computer_use.sqlite3")
    session = ComputerUseSession(goal="observa la pantalla", status=ComputerUseStatus.RUNNING)
    session.record_observation(DesktopObservation(screen_summary="VS Code"))
    session.record_action({"step": "observe", "ok": True})

    store.save(session)
    loaded = store.get(session.id)

    assert loaded is not None
    assert loaded.goal == session.goal
    assert loaded.observations[0]["screen_summary"] == "VS Code"
    assert loaded.actions[0]["ok"] is True


def test_planner_prefers_semantic_capabilities():
    plan = ComputerUsePlanner().create_plan("leer texto visible")

    assert plan.steps[0].capability == "extract_visible_text"
    assert all(step.capability not in {"move_mouse", "click_mouse", "press_key"} for step in plan.steps)


def test_state_manager_detects_visible_text_changes():
    manager = ComputerStateManager()
    manager.update_observation(DesktopObservation(visible_text="antes"))
    changes = manager.update_observation(DesktopObservation(visible_text="despues"))

    assert changes["changed"]
    assert changes["visible_text_changed"]


def test_verifier_checks_text_and_controls():
    observation = DesktopObservation(
        visible_text="resultado OK",
        controls=(UIControl(name="Guardar", control_type="Button"),),
    )
    verifier = ResultVerifier()

    assert verifier.verify_text(observation, "OK")["ok"]
    assert verifier.verify_control_exists(observation, "Guardar")["ok"]
    assert verifier.verify_step(PlanStep("find_ui_control", "buscar", expected={"control_exists": "Guardar"}), observation)["ok"]


def test_uia_service_is_optional_and_safe():
    service = UIAutomationService()

    assert isinstance(service.find_controls(query="Guardar"), tuple)
    sensitive = UIControl(name="password", control_type="Edit", is_password=True)
    try:
        service.set_text(sensitive, "secret")
    except PermissionError as error:
        assert "credenciales" in str(error)
    else:
        raise AssertionError("set_text debe bloquear controles sensibles")


def test_engine_observe_plan_execute_verify_smoke(sandbox):
    async def run():
        runtime = WindowsIntegrationRuntime.build()
        engine = ComputerUseEngine(
            runtime=runtime,
            session_store=ComputerUseSessionStore(sandbox / "computer_use.sqlite3"),
            max_iterations=1,
        )
        session = await engine.run_goal("observa el estado actual", max_iterations=1)
        return session

    session = asyncio.run(run())

    assert session.status == ComputerUseStatus.COMPLETED
    assert session.observations
    assert session.actions
