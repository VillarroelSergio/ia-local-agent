"""Manifest incremental para documentos indexados."""

from __future__ import annotations

import json
from pathlib import Path


class DocumentManifest:
    """Guarda fingerprints y versiones fuera de Chroma."""

    def __init__(self, path: Path):
        self.path = path
        self.items = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}

        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, source_path: str) -> dict | None:
        return self.items.get(source_path)

    def next_version(self, source_path: str, content_hash: str) -> tuple[int, bool]:
        existing = self.get(source_path)

        if not existing:
            return 1, True

        if existing.get("content_hash") == content_hash:
            return int(existing.get("version", 1)), False

        return int(existing.get("version", 1)) + 1, True

    def update(self, source_path: str, payload: dict):
        self.items[source_path] = payload
        self.save()

    def remove(self, source_path: str):
        self.items.pop(source_path, None)
        self.save()
