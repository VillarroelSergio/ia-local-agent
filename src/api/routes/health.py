from __future__ import annotations

from fastapi import APIRouter

from src.api.dependencies import agent_service, event_bus, local_agent

router = APIRouter()


@router.get("/health")
async def health():
    return {"ok": True, "service": "ia-local-agent-api"}


@router.get("/status")
async def status():
    agent = local_agent()
    return {
        "ok": True,
        "provider": agent.provider.name,
        "model": agent.settings.default_model,
        "conversations": len(agent.conversations.conversations),
        "memory": agent.semantic_memory.memory_stats(),
    }


@router.get("/metrics")
async def metrics():
    agent = local_agent()
    return {
        "events_buffered": len(event_bus().history()),
        "active_conversation_messages": agent.conversations.current_length(),
        "provider_metrics": getattr(agent.provider, "last_metrics", None),
        "agent_service": bool(agent_service()),
    }
