import pytest

from src.computer_use.models import (
    DesktopObservation,
    Plan,
    PlanStep,
    PlanStepStatus,
    UIControl,
)
from src.computer_use.planner import ComputerUsePlanner
from src.computer_use.engine import ComputerUseEngine
from src.computer_use.verifier import ResultVerifier
from src.os_integration.models import WindowInfo


@pytest.mark.parametrize(
    ("goal", "capabilities"),
    [
        ("observa el estado", ("summarize_active_window",)),
        ("leer texto visible", ("extract_visible_text",)),
        ("enfoca Visual Studio Code", ("focus_window",)),
        ("completa la tarea", ("summarize_active_window", "run_safe_workflow")),
    ],
)
def test_planner_maps_goals_to_semantic_capabilities(goal, capabilities):
    plan = ComputerUsePlanner().create_plan(goal)

    assert tuple(step.capability for step in plan.steps) == capabilities
    assert all(step.capability not in {"click", "type", "press"} for step in plan.steps)


def test_execution_graph_is_linear_and_references_plan():
    planner = ComputerUsePlanner()
    plan = planner.create_plan("completa la tarea")

    graph = planner.execution_graph(plan)

    assert graph.plan_id == plan.id
    assert graph.nodes == tuple(step.id for step in plan.steps)
    assert graph.edges == ((plan.steps[0].id, plan.steps[1].id),)


def test_next_step_skips_non_pending_steps():
    completed = PlanStep("observe", "done", status=PlanStepStatus.COMPLETED)
    pending = PlanStep("extract_visible_text", "next")
    plan = Plan(goal="goal", steps=(completed, pending))

    assert ComputerUsePlanner().next_step(plan) is pending
    assert ComputerUsePlanner().next_step(Plan(goal="done", steps=(completed,))) is None


def test_verifier_prioritizes_explicit_expectations():
    verifier = ResultVerifier()
    observation = DesktopObservation(
        visible_text="Build completado",
        controls=(UIControl(name="Publicar", control_type="Button"),),
    )

    assert verifier.verify_step(
        PlanStep("focus_window", "focus", expected={"text_contains": "completado"}),
        observation,
        result={"ok": False, "error": "ignored"},
    )["ok"]
    assert verifier.verify_step(
        PlanStep("find_ui_control", "find", expected={"control_exists": "public"}),
        observation,
    )["ok"]


def test_verifier_reports_failed_focus_and_empty_goal():
    verifier = ResultVerifier()
    observation = DesktopObservation()

    assert verifier.verify_step(
        PlanStep("focus_window", "focus"),
        observation,
        result={"ok": False, "error": "window missing"},
    ) == {"ok": False, "reason": "window missing"}
    assert verifier.verify_goal("   ", observation)["ok"] is False


def test_verify_window_matches_title_or_process_case_insensitively():
    observation = DesktopObservation(
        active_window=WindowInfo(
            handle=1,
            title="Proyecto - Visual Studio Code",
            process_name="Code.EXE",
            pid=2,
            rect=None,
            monitor_index=0,
        )
    )
    verifier = ResultVerifier()

    assert verifier.verify_window(observation, "visual studio")["ok"]
    assert verifier.verify_window(observation, "code.exe")["ok"]
    assert verifier.verify_window(DesktopObservation(), "code")["ok"] is False


def test_planner_builds_real_notepad_observe_and_write_plans():
    planner = ComputerUsePlanner()

    observe = planner.create_plan(
        "Abre Notepad con un documento nuevo. Cuando este listo, analiza su ventana."
    )
    write = planner.create_plan(
        "En Notepad, escribe 'Computer Use UAT OK' en el documento."
    )

    assert tuple(step.capability for step in observe.steps) == (
        "open_application",
        "summarize_active_window",
    )
    assert tuple(step.capability for step in write.steps) == ("fill_text_field",)
    assert write.steps[0].args["text"] == "Computer Use UAT OK"


def test_verifier_checks_quoted_text_for_write_goal():
    result = ResultVerifier().verify_goal(
        "Escribe 'Computer Use UAT OK' en el documento.",
        DesktopObservation(visible_text="Computer Use UAT OK"),
    )

    assert result["ok"] is True


def test_resume_plan_starts_at_pending_capability_without_repeating_open():
    plan = ComputerUsePlanner().create_plan(
        "Abre Notepad y escribe 'Computer Use UAT OK' en el documento."
    )

    resumed = ComputerUseEngine._resume_plan_from_capability(plan, "fill_text_field")

    assert tuple(step.capability for step in resumed.steps) == ("fill_text_field",)
