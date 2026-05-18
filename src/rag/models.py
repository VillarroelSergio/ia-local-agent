"""Modelos internos del subsistema RAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RawDocument:
    path: Path
    text: str
    file_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessedDocument:
    doc_id: str
    path: Path
    text: str
    file_type: str
    version: int
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    text: str
    embedding_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    content: str
    metadata: dict[str, Any]
    distance: float | None = None


@dataclass(frozen=True)
class RagSearchResult:
    query: str
    chunks: list[RetrievedChunk]
    trace: dict[str, Any]
