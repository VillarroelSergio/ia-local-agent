from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.dependencies import memory_service
from src.api.schemas.memory import MemoryCreateRequest

router = APIRouter()


@router.get("/memory")
async def list_memory():
    return memory_service().list()


@router.post("/memory")
async def create_memory(request: MemoryCreateRequest):
    return memory_service().remember(request.content, request.category, request.importance)


@router.get("/memory/search")
async def search_memory(query: str, limit: int = 5):
    return memory_service().search(query, limit)


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: str):
    result = memory_service().forget(memory_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/memory/rebuild")
async def rebuild_memory():
    return memory_service().rebuild()


@router.get("/memory/stats")
async def memory_stats():
    return memory_service().stats()
