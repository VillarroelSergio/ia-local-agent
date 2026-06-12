from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.dependencies import computer_use_service
from src.api.schemas.computer_use import (
    ComputerUseCancelResponse,
    ComputerUseObserveRequest,
    ComputerUseRunRequest,
    ComputerUseSessionsResponse,
)

router = APIRouter()


@router.post("/computer-use/run")
async def run_computer_use(request: ComputerUseRunRequest):
    return await computer_use_service().run(request.goal, max_iterations=request.max_iterations)


@router.post("/computer-use/observe")
async def observe_computer_use(request: ComputerUseObserveRequest):
    return await computer_use_service().observe(include_ocr=request.include_ocr)


@router.get("/computer-use/sessions")
async def list_computer_use_sessions(limit: int = 20):
    return ComputerUseSessionsResponse(sessions=computer_use_service().list_sessions(limit=limit))


@router.get("/computer-use/sessions/{session_id}")
async def get_computer_use_session(session_id: str):
    session = computer_use_service().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesion Computer Use no encontrada.")
    return session


@router.post("/computer-use/sessions/{session_id}/cancel")
async def cancel_computer_use_session(session_id: str):
    return ComputerUseCancelResponse(cancelled=computer_use_service().cancel(session_id), session_id=session_id)
