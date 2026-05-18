from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.dependencies import workflow_service
from src.api.schemas.workflows import WorkflowRunRequest

router = APIRouter()


@router.get("/workflows")
async def list_workflows():
    return workflow_service().list()


@router.post("/workflows/{workflow_name}/run")
async def run_workflow(workflow_name: str, request: WorkflowRunRequest):
    run = workflow_service().run(workflow_name, request.input)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow no encontrado.")
    return run


@router.get("/workflows/runs/{run_id}")
async def get_run(run_id: str):
    run = workflow_service().get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run no encontrado.")
    return run


@router.post("/workflows/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    run = workflow_service().cancel(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run no encontrado.")
    return run
