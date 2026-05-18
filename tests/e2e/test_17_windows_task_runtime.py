import asyncio

from src.os_integration.automation import AutomationEngine, WorkflowRunner
from src.os_integration.events import EventBus, EventType, OSEvent
from src.os_integration.models import AutomationStep, AutomationWorkflow
from src.os_integration.scheduler import TaskScheduler
from src.tools import build_tool_registry


def test_semantic_windows_tools_are_registered():
    registry = build_tool_registry()
    expected = {
        "focus_window",
        "move_window",
        "resize_window",
        "maximize_window",
        "minimize_window",
        "close_window",
        "tile_windows_layout",
        "take_screenshot",
        "take_region_screenshot",
        "take_window_screenshot",
        "ocr_active_window",
        "ocr_region",
        "summarize_screen",
        "run_windows_workflow",
    }

    assert expected.issubset(set(registry.names()))
    assert registry.require("run_windows_workflow").metadata.requires_confirmation


def test_event_bus_publishes_to_subscribers():
    received = []

    async def run():
        bus = EventBus()
        bus.subscribe(EventType.CLIPBOARD_CHANGED, lambda event: received.append(event.payload))
        await bus.start()
        await bus.publish(OSEvent(EventType.CLIPBOARD_CHANGED, {"text": "hola"}))
        await asyncio.sleep(0.05)
        await bus.stop()

    asyncio.run(run())

    assert received == [{"text": "hola"}]


def test_workflow_runner_records_action_history_for_safe_wait_step():
    async def run():
        runner = WorkflowRunner(AutomationEngine())
        workflow = AutomationWorkflow(
            name="smoke",
            steps=(AutomationStep(action="wait", args={"seconds": 0.01}, require_confirmation=False),),
        )
        results = await runner.run(workflow)
        return results, runner.history

    results, history = asyncio.run(run())

    assert results[0].ok
    assert history[0].action == "wait"
    assert history[0].ok


def test_task_scheduler_create_list_cancel():
    runner = WorkflowRunner(AutomationEngine())
    scheduler = TaskScheduler(runner)
    workflow = AutomationWorkflow(name="manual", steps=(AutomationStep(action="wait", args={"seconds": 0.01}),))

    task = scheduler.create_task("manual", workflow)

    assert scheduler.list_tasks()[0].id == task.id
    assert scheduler.cancel_task(task.id)
