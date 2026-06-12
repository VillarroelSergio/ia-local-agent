"""Vision provider contracts for a future Computer Use phase."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VisionProvider(ABC):
    name: str

    @abstractmethod
    def analyze(self, image: Any, *, prompt: str) -> dict[str, Any]:
        raise NotImplementedError


class NullVisionProvider(VisionProvider):
    name = "none"

    def analyze(self, image: Any, *, prompt: str) -> dict[str, Any]:
        return {
            "available": False,
            "summary": "",
            "reason": "VisionProvider preparado para fase 2; no hay adaptador activo.",
        }
