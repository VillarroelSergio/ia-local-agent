"""Repositorio ChromaDB para conocimiento documental."""

from __future__ import annotations

from pathlib import Path
import os
from time import monotonic

import chromadb

try:
    from semantic_memory import (
        LMStudioEmbeddingFunction,
        LocalHashEmbeddingFunction,
        SentenceTransformerEmbeddingFunction,
        safe_collection_suffix,
    )
except ModuleNotFoundError:
    from src.semantic_memory import (
        LMStudioEmbeddingFunction,
        LocalHashEmbeddingFunction,
        SentenceTransformerEmbeddingFunction,
        safe_collection_suffix,
    )

from .models import Chunk, RetrievedChunk


class ChromaRagStore:
    """Capa de persistencia y retrieval sobre ChromaDB."""

    def __init__(
        self,
        path: Path,
        *,
        embedding_provider="lmstudio",
        embedding_model="text-embedding-nomic-embed-text-v1.5",
        embedding_base_url="http://127.0.0.1:1234/v1",
        embedding_api_key="lm-studio",
        collection_base="knowledge_documents",
    ):
        self.path = Path(path)
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.embedding_base_url = embedding_base_url
        self.embedding_api_key = embedding_api_key
        self.embedding_cache_path = self.path.parent / "hf_cache"
        self.embedding_function = self._build_embedding_function()
        self.client = chromadb.PersistentClient(path=str(self.path))
        self.collection = self.client.get_or_create_collection(
            name=self._collection_name(collection_base),
            embedding_function=self.embedding_function,
            metadata={
                "description": "Documentacion local indexada para RAG",
                "embedding": self.embedding_function.name(),
            },
        )

    def _build_embedding_function(self):
        provider = (self.embedding_provider or "auto").lower()

        if provider in {"lmstudio", "lm_studio", "openai_compatible"}:
            return LMStudioEmbeddingFunction(
                self.embedding_model,
                self.embedding_base_url,
                self.embedding_api_key,
            )

        if provider in {"auto", "sentence_transformers", "sentence-transformers"}:
            try:
                os.environ.setdefault("HF_HOME", str(self.embedding_cache_path))
                os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
                return SentenceTransformerEmbeddingFunction(
                    self.embedding_model,
                    cache_folder=self.embedding_cache_path,
                )
            except Exception:
                if provider != "auto":
                    raise

        return LocalHashEmbeddingFunction()

    def _collection_name(self, base: str) -> str:
        embedding_name = self.embedding_function.name()

        if embedding_name == "local_hash_embeddings":
            return base

        return f"{base}_{safe_collection_suffix(embedding_name)}"

    def upsert_chunks(self, chunks: list[Chunk]):
        if not chunks:
            return

        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.embedding_text for chunk in chunks],
            metadatas=[self._chroma_metadata(chunk) for chunk in chunks],
        )

    def delete_by_doc_id(self, doc_id: str):
        self.collection.delete(where={"doc_id": doc_id})

    def search(self, query: str, *, top_k=8, filters: dict | None = None) -> tuple[list[RetrievedChunk], dict]:
        started_at = monotonic()
        where = self._where(filters or {})
        count = self.collection.count()

        if count == 0:
            return [], {"collection_count": 0, "retrieval_latency_ms": 0}

        response = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]
        chunks = [
            RetrievedChunk(
                id=item_id,
                content=(metadata or {}).get("display_text") or document,
                metadata=metadata or {},
                distance=distance,
            )
            for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances)
        ]
        trace = {
            "collection_count": count,
            "retrieval_latency_ms": int((monotonic() - started_at) * 1000),
            "filters": filters or {},
            "where": where,
        }
        return chunks, trace

    def _chroma_metadata(self, chunk: Chunk) -> dict:
        metadata = {
            key: value
            for key, value in chunk.metadata.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        }
        metadata["display_text"] = chunk.text
        metadata["chunk_id"] = chunk.id
        metadata["doc_id"] = chunk.doc_id
        return metadata

    def _where(self, filters: dict) -> dict | None:
        clauses = []

        for key in ("doc_id", "file_type", "project_id", "safe_source"):
            value = filters.get(key)
            if value:
                clauses.append({key: value})

        if not clauses:
            return None

        if len(clauses) == 1:
            return clauses[0]

        return {"$and": clauses}
