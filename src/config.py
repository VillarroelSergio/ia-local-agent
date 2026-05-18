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


def env_paths(name, default):
    value = os.getenv(name)

    if value is None:
        return default

    paths = []

    for raw_path in value.split(";"):
        path = raw_path.strip()

        if path:
            paths.append(Path(path).expanduser())

    return paths or default


def default_sensitive_read_roots():
    user_profile = Path.home()
    return [
        Path(PROJECT_ROOT.anchor),
        user_profile / "Documents",
        user_profile / "Desktop",
        user_profile / "Downloads",
        user_profile / "Pictures",
        user_profile / "Videos",
    ]


@dataclass(frozen=True)
class Settings:
    """Configuracion global del backend."""

    project_root: Path
    app_env: str
    default_provider: str
    default_model: str
    lmstudio_base_url: str
    lmstudio_api_key: str
    temperature: float
    lmstudio_minimal_chat: bool
    agent_timing_log_enabled: bool
    agent_timing_log_console: bool
    max_context_tokens: int
    reserved_response_tokens: int
    llm_native_tools_enabled: bool
    tools_require_confirmation: bool
    tool_allowed_roots: list[Path]
    tool_confirm_read_roots: list[Path]
    conversations_path: Path
    chroma_path: Path
    semantic_memory_enabled: bool
    semantic_memory_results: int
    semantic_embedding_provider: str
    semantic_embedding_model: str
    long_term_memory_enabled: bool
    rag_documents_root: Path
    rag_manifest_path: Path
    rag_embedding_provider: str
    rag_embedding_model: str
    rag_chunk_tokens: int
    rag_chunk_overlap_tokens: int
    rag_top_k: int
    log_level: str


def get_settings():
    """Construye Settings desde .env y variables de entorno."""
    load_dotenv()

    return Settings(
        project_root=PROJECT_ROOT,
        app_env=os.getenv("APP_ENV", "dev"),
        default_provider=os.getenv("DEFAULT_PROVIDER", "lmstudio"),
        default_model=os.getenv("DEFAULT_MODEL", "qwen/qwen3.5-9b"),
        lmstudio_base_url=os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1"),
        lmstudio_api_key=os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        lmstudio_minimal_chat=env_bool("LMSTUDIO_MINIMAL_CHAT", True),
        agent_timing_log_enabled=env_bool("AGENT_TIMING_LOG_ENABLED", True),
        agent_timing_log_console=env_bool("AGENT_TIMING_LOG_CONSOLE", True),
        max_context_tokens=env_int("MAX_CONTEXT_TOKENS", 4096),
        reserved_response_tokens=env_int("RESERVED_RESPONSE_TOKENS", 1024),
        llm_native_tools_enabled=env_bool("LLM_NATIVE_TOOLS_ENABLED", False),
        tools_require_confirmation=env_bool("TOOLS_REQUIRE_CONFIRMATION", True),
        tool_allowed_roots=env_paths(
            "TOOL_ALLOWED_ROOTS",
            [PROJECT_ROOT, PROJECT_ROOT.parent],
        ),
        tool_confirm_read_roots=env_paths(
            "TOOL_CONFIRM_READ_ROOTS",
            default_sensitive_read_roots(),
        ),
        conversations_path=PROJECT_ROOT / os.getenv("CONVERSATIONS_PATH", "data/conversations.sqlite3"),
        chroma_path=PROJECT_ROOT / os.getenv("CHROMA_PATH", "data/chroma"),
        semantic_memory_enabled=env_bool("SEMANTIC_MEMORY_ENABLED", True),
        semantic_memory_results=env_int("SEMANTIC_MEMORY_RESULTS", 5),
        semantic_embedding_provider=os.getenv("SEMANTIC_EMBEDDING_PROVIDER", "lmstudio"),
        semantic_embedding_model=os.getenv(
            "SEMANTIC_EMBEDDING_MODEL",
            "text-embedding-nomic-embed-text-v1.5",
        ),
        long_term_memory_enabled=env_bool("LONG_TERM_MEMORY_ENABLED", True),
        rag_documents_root=PROJECT_ROOT / os.getenv("RAG_DOCUMENTS_ROOT", ".."),
        rag_manifest_path=PROJECT_ROOT / os.getenv("RAG_MANIFEST_PATH", "data/rag_manifest.json"),
        rag_embedding_provider=os.getenv("RAG_EMBEDDING_PROVIDER", os.getenv("SEMANTIC_EMBEDDING_PROVIDER", "lmstudio")),
        rag_embedding_model=os.getenv(
            "RAG_EMBEDDING_MODEL",
            os.getenv(
                "SEMANTIC_EMBEDDING_MODEL",
                "text-embedding-nomic-embed-text-v1.5",
            ),
        ),
        rag_chunk_tokens=env_int("RAG_CHUNK_TOKENS", 750),
        rag_chunk_overlap_tokens=env_int("RAG_CHUNK_OVERLAP_TOKENS", 120),
        rag_top_k=env_int("RAG_TOP_K", 8),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
