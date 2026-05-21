from __future__ import annotations

from fastapi import APIRouter

from src.api.dependencies import settings_service
from src.api.schemas.settings import SettingsPatchRequest, SettingsResponse

router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    return settings_service().get()


@router.patch("/settings", response_model=SettingsResponse)
async def patch_settings(request: SettingsPatchRequest):
    return settings_service().patch(request.values)
