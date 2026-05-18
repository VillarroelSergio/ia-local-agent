from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.dependencies import agent_service, local_agent
from src.api.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return await agent_service().chat(request)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def events():
        async for chunk in agent_service().stream_chat(request):
            yield f"event: {chunk.type}\n"
            yield f"data: {json.dumps(chunk.model_dump(), ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/chat/sessions")
async def sessions():
    return [
        {
            "id": item.id,
            "title": item.title,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "message_count": len(item.messages),
        }
        for item in local_agent().conversations.list_conversations()
    ]


@router.get("/chat/sessions/{session_id}")
async def get_session(session_id: str):
    conversation = local_agent().conversations.get_conversation(session_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversacion no encontrada.")
    return conversation


@router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: str):
    if not local_agent().conversations.delete_conversation(session_id):
        raise HTTPException(status_code=404, detail="Conversacion no encontrada.")
    return {"deleted": session_id}
