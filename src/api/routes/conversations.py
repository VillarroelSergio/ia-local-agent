from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.dependencies import local_agent
from src.api.schemas.conversations import ConversationCreateRequest, ConversationUpdateRequest

router = APIRouter()


def serialize(conversation):
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "summary": conversation.summary,
        "message_count": len(conversation.messages),
    }


@router.get("/conversations")
async def list_conversations():
    return [serialize(item) for item in local_agent().conversations.list_conversations()]


@router.post("/conversations")
async def create_conversation(request: ConversationCreateRequest):
    return serialize(local_agent().conversations.create_conversation(request.title))


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conversation = local_agent().conversations.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversacion no encontrada.")
    return serialize(conversation)


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: str, request: ConversationUpdateRequest):
    try:
        return serialize(local_agent().conversations.rename_conversation(conversation_id, request.title))
    except KeyError:
        raise HTTPException(status_code=404, detail="Conversacion no encontrada.") from None


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    if not local_agent().conversations.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversacion no encontrada.")
    return {"deleted": conversation_id}


@router.get("/conversations/{conversation_id}/messages")
async def conversation_messages(conversation_id: str, limit: int = 50, offset: int = 0):
    conversation = local_agent().conversations.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversacion no encontrada.")
    selected = conversation.messages[offset:offset + limit]
    return {"items": selected, "total": len(conversation.messages), "limit": limit, "offset": offset}
