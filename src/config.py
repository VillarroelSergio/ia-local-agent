"""Configuracion central del agente local.

Este modulo evita que valores como el modelo, endpoint del provider o limites
de contexto queden repartidos por el backend. Lee variables de entorno y ofrece
un objeto Settings sencillo que puede sustituirse por pydantic-settings mas
adelante sin cambiar el resto de capas.
"""

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path=None):
    """Carga un archivo .env simple si existe.

    No sobrescribe variables ya definidas en el entorno del proceso.
    """
    env_path = Path(path) if path else PROJECT_ROOT / ".env"

    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        os.environ.setdefault(key, value)


def env_bool(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "si", "s"}


def env_int(name, default):
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Configuracion global del backend."""

    app_env: str
    default_provider: str
    default_model: str
    lmstudio_base_url: str
    lmstudio_api_key: str
    temperature: float
    max_context_tokens: int
    reserved_response_tokens: int
    tools_require_confirmation: bool
    conversations_path: Path
    chroma_path: Path
    semantic_memory_enabled: bool
    semantic_memory_results: int
    log_level: str


def get_settings():
    """Construye Settings desde .env y variables de entorno."""
    load_dotenv()

    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        default_provider=os.getenv("DEFAULT_PROVIDER", "lmstudio"),
        default_model=os.getenv("DEFAULT_MODEL", "qwen/qwen3.5-9b"),
        lmstudio_base_url=os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1"),
        lmstudio_api_key=os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_context_tokens=env_int("MAX_CONTEXT_TOKENS", 4096),
        reserved_response_tokens=env_int("RESERVED_RESPONSE_TOKENS", 1024),
        tools_require_confirmation=env_bool("TOOLS_REQUIRE_CONFIRMATION", True),
        conversations_path=PROJECT_ROOT / os.getenv("CONVERSATIONS_PATH", "data/conversations.sqlite3"),
        chroma_path=PROJECT_ROOT / os.getenv("CHROMA_PATH", "data/chroma"),
        semantic_memory_enabled=env_bool("SEMANTIC_MEMORY_ENABLED", True),
        semantic_memory_results=env_int("SEMANTIC_MEMORY_RESULTS", 5),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
