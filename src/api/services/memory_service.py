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
