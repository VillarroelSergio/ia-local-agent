from __future__ import annotations

from src.semantic_memory import SemanticMemoryManager


class MemoryService:
    def __init__(self, memory: SemanticMemoryManager, agent=None):
        self.memory = memory
        self.agent = agent

    def list(self):
        return self.memory.list_memories()

    def remember(self, content, category="explicit", importance=5):
        return self.memory.remember(content, category=category, importance=importance, source="api")

    def search(self, query, limit=5):
        return [
            {"id": item.id, "content": item.content, "metadata": item.metadata, "distance": item.distance}
            for item in self.memory.search(query, max_results=limit)
        ]

    def forget(self, memory_id):
        return self.memory.forget(memory_id)

    def stats(self):
        return self.memory.memory_stats()

    def rebuild(self):
        if self.agent is None:
            return self.stats()
        return self.agent.rebuild_semantic_memory()

    def rag_stats(self):
        if self.agent is None or not hasattr(self.agent, "rag"):
            return {"available": False}
        data = self.agent.rag.stats()
        data["available"] = True
        return data

    def rag_index(self, path, project_id="default", force=False):
        if self.agent is None or not hasattr(self.agent, "rag"):
            return {"available": False, "error": "RAG no disponible."}
        return self.agent.rag.index_path(path, project_id=project_id, force=force)

    def rag_documents(self):
        if self.agent is None or not hasattr(self.agent, "rag"):
            return {"available": False, "documents": []}
        documents = []
        for source_path, payload in self.agent.rag.manifest.items.items():
            item = dict(payload)
            item["source_path"] = source_path
            documents.append(item)
        documents.sort(key=lambda item: item.get("indexed_at", ""), reverse=True)
        return {"available": True, "count": len(documents), "documents": documents}
