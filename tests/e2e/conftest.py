"""Fixtures end-to-end seguras para el agente local."""

from __future__ import annotations

import sys
import shutil
from uuid import uuid4
from dataclasses import replace
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.config import get_settings  # noqa: E402
from src.conversations import ConversationManager, ConversationStore  # noqa: E402
from src.semantic_memory import SemanticMemoryManager  # noqa: E402


@pytest.fixture()
def sandbox():
    runtime_root = PROJECT_ROOT / "tests" / "sandbox" / "runtime"
    root = runtime_root / uuid4().hex
    root.mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "data").mkdir()

    try:
        yield root
    finally:
        if root.exists() and runtime_root in root.parents:
            shutil.rmtree(root, ignore_errors=True)


@pytest.fixture()
def test_settings(sandbox):
    base = get_settings()
    data_dir = sandbox / "data"
    data_dir.mkdir(exist_ok=True)
    return replace(
        base,
        default_provider="lmstudio",
        default_model="fake-model",
        lmstudio_base_url="http://127.0.0.1:1234/v1",
        conversations_path=data_dir / "conversations.sqlite3",
        chroma_path=data_dir / "chroma",
        semantic_embedding_provider="local_hash",
        semantic_embedding_model="local-hash",
        rag_documents_root=sandbox,
        rag_manifest_path=data_dir / "rag_manifest.json",
        rag_embedding_provider="local_hash",
        rag_embedding_model="local-hash",
        tool_allowed_roots=[sandbox, data_dir],
        tool_confirm_read_roots=[sandbox],
        llm_native_tools_enabled=True,
        tools_require_confirmation=True,
    )


@pytest.fixture()
def conversation_manager(tmp_path):
    return ConversationManager(ConversationStore(tmp_path / "conversations.sqlite3"))


@pytest.fixture()
def semantic_memory(tmp_path):
    return SemanticMemoryManager(
        path=tmp_path / "chroma",
        enabled=True,
        embedding_provider="local_hash",
        embedding_model="local-hash",
        long_term_enabled=True,
    )
