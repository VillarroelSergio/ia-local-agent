from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from src.orchestration import workflows


class WorkflowService:
    def __init__(self):
        self.definitions = {
            value["name"]: value
            for value in (
                workflows.FILE_SEARCH_WORKFLOW,
                workflows.CODE_DEBUG_WORKFLOW,
                workflows.WINDOWS_AUTOMATION_WORKFLOW,
                workflows.RAG_TOOL_WORKFLOW,
            )
        }
        self.runs = {}

    def list(self):
        return list(self.definitions.values())

    def run(self, name, input_=None):
        if name not in self.definitions:
            return None
        run_id = uuid4().hex
        logs = [
            {"timestamp": datetime.now().isoformat(timespec="seconds"), "step": step, "status": "queued"}
            for step in self.definitions[name]["steps"]
        ]
        info = {"run_id": run_id, "workflow_name": name, "status": "completed", "progress": 1.0, "logs": logs}
        self.runs[run_id] = info
        return info

    def get(self, run_id):
        return self.runs.get(run_id)

    def cancel(self, run_id):
        run = self.runs.get(run_id)
        if not run:
            return None
        run["status"] = "cancelled"
        return run
