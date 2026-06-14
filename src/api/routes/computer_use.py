from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.dependencies import computer_use_service
from src.api.schemas.computer_use import (
    ComputerUseCancelResponse,
    ComputerUseCapabilityRequest,
    ComputerUseConfirmationRequest,
    ComputerUseConfirmationResponse,
    ComputerUseCreateRequest,
    ComputerUseFindControlRequest,
    ComputerUseObserveRequest,
    ComputerUseObserveWindowRequest,
    ComputerUseRunRequest,
    ComputerUseSessionsResponse,
)

router = APIRouter()


@router.get("/computer-use/status")
async def computer_use_status():
    return computer_use_service().status()


@router.post("/computer-use/run")
async def run_computer_use(request: ComputerUseRunRequest):
    return await computer_use_service().run(request.goal, max_iterations=request.max_iterations)


@router.post("/computer-use/sessions", status_code=201)
async def create_computer_use_session(request: ComputerUseCreateRequest):
    return await computer_use_service().create(request.goal)


@router.post("/computer-use/sessions/{session_id}/run")
async def run_computer_use_session(session_id: str, max_iterations: int = 3):
    try:
        return await computer_use_service().run_session(session_id, max_iterations=max_iterations)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/computer-use/observe")
async def observe_computer_use(request: ComputerUseObserveRequest):
    return await computer_use_service().observe(include_ocr=request.include_ocr)


@router.post("/computer-use/observe/window")
async def observe_computer_use_window(request: ComputerUseObserveWindowRequest):
    return computer_use_service().observe_window(
        window_handle=request.window_handle, include_ocr=request.include_ocr
    )


@router.post("/computer-use/find-control")
async def find_computer_use_control(request: ComputerUseFindControlRequest):
    return computer_use_service().find_control(request.query, window_handle=request.window_handle)


@router.post("/computer-use/execute-capability")
async def execute_computer_use_capability(request: ComputerUseCapabilityRequest):
    try:
        return await computer_use_service().execute_capability(
            request.capability, request.arguments,
            session_id=request.session_id, approved=request.approved,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


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


@router.post("/computer-use/sessions/{session_id}/confirm", response_model=ComputerUseConfirmationResponse)
async def confirm_computer_use_session(session_id: str, request: ComputerUseConfirmationRequest):
    try:
        return await computer_use_service().confirm(session_id, request.approved)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
