"""Memoria semantica local basada en ChromaDB.

La funcion de embeddings incluida es local y determinista. No compite con un
modelo de embeddings real, pero permite tener Chroma integrado sin depender de
descargas. Mas adelante se puede sustituir por sentence-transformers u Ollama
embeddings manteniendo esta interfaz.
"""

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import chromadb


TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


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


@dataclass
class SemanticResult:
    id: str
    content: str
    metadata: dict
    distance: float | None = None


class SemanticMemoryManager:
    """Gestiona colecciones Chroma para memoria y conversaciones."""

    def __init__(self, path, enabled=True, max_results=5):
        self.path = Path(path)
        self.enabled = enabled
        self.max_results = max_results
        self.embedding_function = LocalHashEmbeddingFunction()
        self.client = None
        self.memories = None
        self.conversation_messages = None

        if self.enabled:
            self.initialize()

    def initialize(self):
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.path))
        self.memories = self.client.get_or_create_collection(
            name="explicit_memories",
            embedding_function=self.embedding_function,
            metadata={"description": "Recuerdos explicitos del usuario"},
        )
        self.conversation_messages = self.client.get_or_create_collection(
            name="conversation_messages",
            embedding_function=self.embedding_function,
            metadata={"description": "Mensajes conversacionales persistidos"},
        )

    def remember(self, content):
        """Guarda un recuerdo explicito directamente en ChromaDB."""
        content = content.strip()

        if not content:
            return {"error": "No hay contenido para recordar."}

        memory = {
            "id": uuid4().hex[:8],
            "content": content,
            "created_at": datetime.now().isoformat(timespec="seconds"),
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
            })

        memories.sort(key=lambda memory: memory.get("created_at", ""))
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
        return results[:limit]

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
