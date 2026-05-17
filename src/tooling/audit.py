"""Auditoria local ligera para tool calls y workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AuditEvent:
    event_type: str
    payload: dict[str, Any]


class JsonlAuditLog:
    """Log append-only en JSONL. Suficiente para la primera fase local."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else None

        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event_type: str, **payload):
        if self.path is None:
            return

        event = {
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "event_type": event_type,
            "payload": payload,
        }
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            return
