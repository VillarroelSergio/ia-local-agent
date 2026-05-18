"""In-process scheduler for recurring and event-triggered workflows."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta

from .automation import WorkflowRunner
from .events import EventBus, EventType, OSEvent
from .models import AutomationWorkflow, ScheduledTask, TaskStatus


class TaskScheduler:
    """Small async scheduler designed to be replaced by a durable backend later."""

    def __init__(self, workflow_runner: WorkflowRunner, *, event_bus: EventBus | None = None):
        self.workflow_runner = workflow_runner
        self.event_bus = event_bus
        self._tasks: dict[str, ScheduledTask] = {}
        self._runner_task: asyncio.Task | None = None
        self._closed = asyncio.Event()

    def create_task(
        self,
        name: str,
        workflow: AutomationWorkflow,
        *,
        trigger: str = "manual",
        interval_seconds: float | None = None,
        enabled: bool = True,
    ) -> ScheduledTask:
        next_run_at = datetime.now() + timedelta(seconds=interval_seconds) if interval_seconds else None
        task = ScheduledTask(
            name=name,
            workflow=workflow,
            trigger=trigger,
            interval_seconds=interval_seconds,
            enabled=enabled,
            next_run_at=next_run_at,
        )
        self._tasks[task.id] = task
        return task

    def list_tasks(self) -> tuple[ScheduledTask, ...]:
        return tuple(self._tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        self.workflow_runner.cancel(task.workflow.id)
        self._tasks[task_id] = replace(task, enabled=False, status=TaskStatus.CANCELLED)
        return True

    async def run_task_now(self, task_id: str):
        task = self._tasks[task_id]
        self._tasks[task_id] = replace(task, status=TaskStatus.RUNNING)
        results = await self.workflow_runner.run(task.workflow)
        status = TaskStatus.COMPLETED if all(result.ok for result in results) else TaskStatus.FAILED
        current = self._tasks[task_id]
        next_run_at = None
        if current.interval_seconds and current.enabled:
            next_run_at = datetime.now() + timedelta(seconds=current.interval_seconds)
        self._tasks[task_id] = replace(current, status=status, next_run_at=next_run_at)
        return results

    async def start(self) -> None:
        if self._runner_task is None or self._runner_task.done():
            self._closed.clear()
            self._runner_task = asyncio.create_task(self._loop(), name="windows-task-scheduler")

    async def stop(self) -> None:
        self._closed.set()
        if self._runner_task:
            self._runner_task.cancel()
            try:
                await self._runner_task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while not self._closed.is_set():
            now = datetime.now()
            for task in list(self._tasks.values()):
                if task.enabled and task.next_run_at and task.next_run_at <= now:
                    if self.event_bus:
                        await self.event_bus.publish(OSEvent(EventType.AUTOMATION_STARTED, {
                            "task_id": task.id,
                            "workflow": task.workflow.name,
                        }))
                    await self.run_task_now(task.id)
            await asyncio.sleep(0.5)
