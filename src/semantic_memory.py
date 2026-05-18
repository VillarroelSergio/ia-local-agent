"""Memoria semantica local basada en ChromaDB."""

import hashlib
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import chromadb
from openai import OpenAI


TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)
MEMORY_PREFIX_PATTERN = re.compile(
    r"^\s*(?:recuerda que|recordar que|remember that)\s+(.+)$",
    re.IGNORECASE,
)
PROFILE_PATTERNS = [
    re.compile(r"\bmi nombre es\s+(.+)", re.IGNORECASE),
    re.compile(r"\bme llamo\s+(.+)", re.IGNORECASE),
    re.compile(r"\bprefiero\s+(.+)", re.IGNORECASE),
    re.compile(r"\bme gusta\s+(.+)", re.IGNORECASE),
    re.compile(r"\bno me gusta\s+(.+)", re.IGNORECASE),
    re.compile(r"\buso\s+(.+)", re.IGNORECASE),
    re.compile(r"\btrabajo (?:con|en)\s+(.+)", re.IGNORECASE),
    re.compile(r"\bsoy\s+(.+)", re.IGNORECASE),
]


def safe_collection_suffix(value):
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", value.lower()).strip("_")
    return f"{clean[:32]}_{digest}"


class LocalHashEmbeddingFunction:
    """Embedding local simple mediante hashing de tokens."""

    def __init__(self, dimensions=384):
        self.dimensions = dimensions

    def name(self):
        return "local_hash_embeddings"

    def __call__(self, input):
        return [self.embed(text) for text in input]

    def embed_query(self, input):
        return self.__call__(input)

    def embed_documents(self, input):
        return self.__call__(input)

    def embed(self, text):
        vector = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall((text or "").lower())

        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))

        if not norm:
            return vector

        return [value / norm for value in vector]


class SentenceTransformerEmbeddingFunction:
    """Embedding local real usando sentence-transformers."""

    def __init__(self, model_name, cache_folder=None):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(
            model_name,
            cache_folder=str(cache_folder) if cache_folder else None,
        )

    def name(self):
        return f"sentence_transformers:{self.model_name}"

    def __call__(self, input):
        embeddings = self.model.encode(
            input,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, input):
        return self.__call__(input)

    def embed_documents(self, input):
        return self.__call__(input)


class LMStudioEmbeddingFunction:
    """Embedding local usando el endpoint OpenAI-compatible de LM Studio."""

    def __init__(self, model_name, base_url, api_key):
        self.model_name = model_name
        self.base_url = base_url
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def name(self):
        return f"lmstudio:{self.model_name}"

    def __call__(self, input):
        response = self.client.embeddings.create(
            model=self.model_name,
            input=input,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, input):
        return self.__call__(input)

    def embed_documents(self, input):
        return self.__call__(input)


@dataclass
class SemanticResult:
    id: str
    content: str
    metadata: dict
    distance: float | None = None


class SemanticMemoryManager:
    """Gestiona colecciones Chroma para memoria y conversaciones."""

    def __init__(
        self,
        path,
        enabled=True,
        max_results=5,
        embedding_provider="lmstudio",
        embedding_model="text-embedding-nomic-embed-text-v1.5",
        embedding_base_url="http://127.0.0.1:1234/v1",
        embedding_api_key="lm-studio",
        long_term_enabled=True,
    ):
        self.path = Path(path)
        self.enabled = enabled
        self.max_results = max_results
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.embedding_base_url = embedding_base_url
        self.embedding_api_key = embedding_api_key
        self.long_term_enabled = long_term_enabled
        self.embedding_cache_path = self.path.parent / "hf_cache"
        self.embedding_function = self.build_embedding_function()
        self.client = None
        self.memories = None
        self.conversation_messages = None

        if self.enabled:
            self.initialize()

    def initialize(self):
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.path))
        collection_suffix = self.collection_suffix()
        memories_name = self.collection_name("explicit_memories", collection_suffix)
        messages_name = self.collection_name("conversation_messages", collection_suffix)
        self.memories = self.client.get_or_create_collection(
            name=memories_name,
            embedding_function=self.embedding_function,
            metadata={
                "description": "Recuerdos explicitos del usuario",
                "embedding": self.embedding_function.name(),
            },
        )
        self.conversation_messages = self.client.get_or_create_collection(
            name=messages_name,
            embedding_function=self.embedding_function,
            metadata={
                "description": "Mensajes conversacionales persistidos",
                "embedding": self.embedding_function.name(),
            },
        )

    def build_embedding_function(self):
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

    def collection_suffix(self):
        embedding_name = self.embedding_function.name()

        if embedding_name == "local_hash_embeddings":
            return ""

        return safe_collection_suffix(embedding_name)

    def collection_name(self, base_name, suffix):
        if not suffix:
            return base_name

        return f"{base_name}_{suffix}"

    def remember(self, content, *, category="explicit", importance=5, source="manual"):
        """Guarda un recuerdo explicito directamente en ChromaDB."""
        content = content.strip()

        if not content:
            return {"error": "No hay contenido para recordar."}

        memory = {
            "id": uuid4().hex[:8],
            "content": content,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "category": category,
            "importance": int(importance),
            "source": source,
            "access_count": 0,
        }
        self.add_memory(memory)
        return memory

    def add_memory(self, memory):
        if not self.enabled or "error" in memory:
            return

        content = memory.get("content", "")
        memory_id = memory.get("id")

        if not content or not memory_id:
            return

        self.memories.upsert(
            ids=[memory_id],
            documents=[content],
            metadatas=[{
                "type": "explicit_memory",
                "created_at": memory.get("created_at", ""),
                "updated_at": memory.get("updated_at", memory.get("created_at", "")),
                "category": memory.get("category", "explicit"),
                "importance": int(memory.get("importance", 5)),
                "source": memory.get("source", "manual"),
                "access_count": int(memory.get("access_count", 0)),
                "last_accessed_at": memory.get("last_accessed_at", ""),
            }],
        )

    def list_memories(self):
        """Lista recuerdos explicitos guardados en ChromaDB."""
        if not self.enabled:
            return []

        response = self.memories.get(include=["documents", "metadatas"])
        ids = response.get("ids", [])
        documents = response.get("documents", [])
        metadatas = response.get("metadatas", [])
        memories = []

        for memory_id, document, metadata in zip(ids, documents, metadatas):
            memories.append({
                "id": memory_id,
                "content": document,
                "created_at": (metadata or {}).get("created_at", ""),
                "updated_at": (metadata or {}).get("updated_at", ""),
                "category": (metadata or {}).get("category", "explicit"),
                "importance": (metadata or {}).get("importance", 5),
                "source": (metadata or {}).get("source", "manual"),
                "access_count": (metadata or {}).get("access_count", 0),
                "last_accessed_at": (metadata or {}).get("last_accessed_at", ""),
            })

        memories.sort(key=lambda memory: (
            int(memory.get("importance", 5)),
            memory.get("updated_at") or memory.get("created_at", ""),
        ))
        return memories

    def forget(self, memory_id):
        """Elimina un recuerdo explicito de ChromaDB."""
        if not self.enabled:
            return {"error": "La memoria semantica esta desactivada."}

        existing = self.memories.get(ids=[memory_id])

        if not existing.get("ids"):
            return {"error": f"No existe una memoria con id: {memory_id}"}

        self.delete_memory(memory_id)
        return {"deleted": memory_id}

    def delete_memory(self, memory_id):
        if not self.enabled:
            return

        self.memories.delete(ids=[memory_id])

    def memory_stats(self):
        if not self.enabled:
            return {"enabled": False}

        return {
            "enabled": True,
            "embedding": self.embedding_function.name(),
            "explicit_memories": self.memories.count(),
            "conversation_messages": self.conversation_messages.count(),
            "long_term_enabled": self.long_term_enabled,
        }

    def add_conversation_message(self, message):
        if not self.enabled or message.role not in {"user", "assistant"}:
            return

        if not message.content:
            return

        self.conversation_messages.upsert(
            ids=[message.id],
            documents=[message.content],
            metadatas=[{
                "type": "conversation_message",
                "role": message.role,
                "conversation_id": message.conversation_id or "",
                "created_at": message.created_at,
            }],
        )

        if message.role == "user":
            self.promote_long_term_memory(message.content)

    def delete_conversation_messages(self, message_ids):
        if not self.enabled or not message_ids:
            return

        self.conversation_messages.delete(ids=message_ids)

    def search(self, query, max_results=None):
        if not self.enabled or not query:
            return []

        limit = max_results or self.max_results
        results = []
        results.extend(self.search_collection(self.memories, query, limit))
        results.extend(self.search_collection(self.conversation_messages, query, limit))
        results.sort(key=lambda result: result.distance if result.distance is not None else 999)
        selected = results[:limit]
        self.touch_explicit_memories(selected)
        return selected

    def search_collection(self, collection, query, limit):
        if collection.count() == 0:
            return []

        response = collection.query(
            query_texts=[query],
            n_results=min(limit, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]

        return [
            SemanticResult(
                id=item_id,
                content=document,
                metadata=metadata or {},
                distance=distance,
            )
            for item_id, document, metadata, distance in zip(
                ids,
                documents,
                metadatas,
                distances,
            )
        ]

    def touch_explicit_memories(self, results):
        memory_ids = [
            result.id for result in results
            if result.metadata.get("type") == "explicit_memory"
        ]

        if not memory_ids:
            return

        response = self.memories.get(
            ids=memory_ids,
            include=["documents", "metadatas"],
        )
        now = datetime.now().isoformat(timespec="seconds")

        for memory_id, document, metadata in zip(
            response.get("ids", []),
            response.get("documents", []),
            response.get("metadatas", []),
        ):
            metadata = metadata or {}
            metadata["access_count"] = int(metadata.get("access_count", 0)) + 1
            metadata["last_accessed_at"] = now
            self.memories.upsert(
                ids=[memory_id],
                documents=[document],
                metadatas=[metadata],
            )

    def promote_long_term_memory(self, text):
        if not self.enabled or not self.long_term_enabled:
            return None

        candidate = self.extract_memory_candidate(text)

        if candidate is None:
            return None

        existing = self.find_duplicate_memory(candidate["content"])

        if existing:
            return self.refresh_memory(existing, candidate)

        return self.remember(
            candidate["content"],
            category=candidate["category"],
            importance=candidate["importance"],
            source="auto",
        )

    def extract_memory_candidate(self, text):
        cleaned = " ".join((text or "").strip().split())

        if len(cleaned) < 8 or len(cleaned) > 500:
            return None

        prefix_match = MEMORY_PREFIX_PATTERN.match(cleaned)

        if prefix_match:
            return {
                "content": prefix_match.group(1).strip(),
                "category": "explicit",
                "importance": 8,
            }

        for pattern in PROFILE_PATTERNS:
            match = pattern.search(cleaned)

            if match:
                return {
                    "content": cleaned,
                    "category": "profile",
                    "importance": 7,
                }

        return None

    def find_duplicate_memory(self, content):
        normalized = self.normalize_memory_text(content)

        for memory in self.list_memories():
            if self.normalize_memory_text(memory.get("content", "")) == normalized:
                return SemanticResult(
                    id=memory["id"],
                    content=memory["content"],
                    metadata=memory,
                )

        matches = self.search_collection(self.memories, content, 3)

        for match in matches:
            if match.distance is not None and match.distance <= 0.12:
                return match

        return None

    def refresh_memory(self, existing, candidate):
        now = datetime.now().isoformat(timespec="seconds")
        metadata = {
            **existing.metadata,
            "type": "explicit_memory",
            "updated_at": now,
            "category": candidate.get("category", existing.metadata.get("category", "explicit")),
            "importance": max(
                int(existing.metadata.get("importance", 5)),
                int(candidate.get("importance", 5)),
            ),
            "source": existing.metadata.get("source", "auto"),
            "access_count": int(existing.metadata.get("access_count", 0)),
            "last_accessed_at": existing.metadata.get("last_accessed_at", ""),
        }
        self.memories.upsert(
            ids=[existing.id],
            documents=[existing.content],
            metadatas=[metadata],
        )
        return {"updated": existing.id, "content": existing.content}

    def normalize_memory_text(self, text):
        return " ".join(TOKEN_PATTERN.findall((text or "").lower()))

    def format_explicit_for_prompt(self, limit=20):
        memories = self.list_memories()

        if not memories:
            return "No hay memoria persistente guardada todavia."

        recent_memories = memories[-limit:]
        return "\n".join(
            f"- [{memory.get('id')}] {memory.get('content')}"
            for memory in recent_memories
        )

    def format_for_prompt(self, query):
        results = self.search(query)

        if not results:
            return "No hay memoria semantica relevante."

        lines = []

        for result in results:
            source = result.metadata.get("type", "semantic")
            role = result.metadata.get("role")
            label = f"{source}:{role}" if role else source
            lines.append(f"- [{label}:{result.id}] {result.content}")

        return "\n".join(lines)
