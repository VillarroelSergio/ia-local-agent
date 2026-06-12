from __future__ import annotations

from functools import lru_cache

from fastapi import Request

from src.agent import LocalAgent
from src.api.config import ApiSettings, get_api_settings
from src.api.services.chat_service import AgentService
from src.api.services.computer_use_service import ComputerUseService
from src.api.services.event_service import EventBus
from src.api.services.memory_service import MemoryService
from src.api.services.settings_service import SettingsService
from src.api.services.tool_service import ToolService
from src.api.services.workflow_service import WorkflowService


@lru_cache(maxsize=1)
def api_settings() -> ApiSettings:
    return get_api_settings()


@lru_cache(maxsize=1)
def event_bus() -> EventBus:
    return EventBus()


@lru_cache(maxsize=1)
def local_agent() -> LocalAgent:
    return LocalAgent()


@lru_cache(maxsize=1)
def agent_service() -> AgentService:
    return AgentService(local_agent(), event_bus())


@lru_cache(maxsize=1)
def tool_service() -> ToolService:
    return ToolService()


@lru_cache(maxsize=1)
def memory_service() -> MemoryService:
    agent = local_agent()
    return MemoryService(agent.semantic_memory, agent=agent)


@lru_cache(maxsize=1)
def settings_service() -> SettingsService:
    return SettingsService()


@lru_cache(maxsize=1)
def workflow_service() -> WorkflowService:
    return WorkflowService()


@lru_cache(maxsize=1)
def computer_use_service() -> ComputerUseService:
    return ComputerUseService()


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")
