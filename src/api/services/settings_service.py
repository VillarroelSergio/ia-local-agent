from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, get_settings


SETTING_KEYS = {
    "LMSTUDIO_BASE_URL": "str",
    "LMSTUDIO_API_KEY": "secret",
    "DEFAULT_MODEL": "str",
    "LLM_TEMPERATURE": "float",
    "MAX_CONTEXT_TOKENS": "int",
    "RESERVED_RESPONSE_TOKENS": "int",
    "TOOLS_REQUIRE_CONFIRMATION": "bool",
    "CHROMA_PATH": "path",
    "RAG_DOCUMENTS_ROOT": "path",
    "RAG_TOP_K": "int",
}


class SettingsService:
    """Safe .env-backed settings adapter for desktop UI configuration."""

    def __init__(self, env_path: Path | None = None):
        configured = os.getenv("SETTINGS_ENV_PATH")
        self.env_path = env_path or (Path(configured) if configured else PROJECT_ROOT / ".env")

    def get(self) -> dict[str, Any]:
        settings = get_settings()
        values = {
            "LMSTUDIO_BASE_URL": settings.lmstudio_base_url,
            "LMSTUDIO_API_KEY": self._mask(settings.lmstudio_api_key),
            "DEFAULT_MODEL": settings.default_model,
            "LLM_TEMPERATURE": settings.temperature,
            "MAX_CONTEXT_TOKENS": settings.max_context_tokens,
            "RESERVED_RESPONSE_TOKENS": settings.reserved_response_tokens,
            "TOOLS_REQUIRE_CONFIRMATION": settings.tools_require_confirmation,
            "CHROMA_PATH": str(settings.chroma_path),
            "RAG_DOCUMENTS_ROOT": str(settings.rag_documents_root),
            "RAG_TOP_K": settings.rag_top_k,
        }
        return {
            "values": values,
            "metadata": {
                "env_path": str(self.env_path),
                "secret_fields": ["LMSTUDIO_API_KEY"],
                "requires_restart": True,
            },
        }

    def patch(self, updates: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, str] = {}
        for key, value in updates.items():
            if key not in SETTING_KEYS:
                continue
            if value is None or value == "":
                continue
            if SETTING_KEYS[key] == "secret" and self._looks_masked(str(value)):
                continue
            clean[key] = self._coerce(key, value)

        if clean:
            current = self._read_env()
            current.update(clean)
            self._write_env(current)
            os.environ.update(clean)

        return self.get()

    def _read_env(self) -> dict[str, str]:
        if not self.env_path.exists():
            return {}
        values: dict[str, str] = {}
        for raw in self.env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        return values

    def _write_env(self, values: dict[str, str]) -> None:
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"{key}={value}" for key, value in sorted(values.items())]
        self.env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _mask(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 4:
            return "****"
        return f"{value[:2]}{'*' * max(4, len(value) - 4)}{value[-2:]}"

    @staticmethod
    def _looks_masked(value: str) -> bool:
        return "*" in value and len(value) >= 4

    @staticmethod
    def _coerce(key: str, value: Any) -> str:
        kind = SETTING_KEYS[key]
        if kind == "bool":
            return "true" if bool(value) else "false"
        if kind == "int":
            return str(int(value))
        if kind == "float":
            return str(float(value))
        return str(value).strip()
