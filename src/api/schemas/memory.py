from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=5000)
    category: str = "explicit"
    importance: int = Field(default=5, ge=1, le=10)


class MemorySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=50)


class MemoryItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    distance: float | None = None
