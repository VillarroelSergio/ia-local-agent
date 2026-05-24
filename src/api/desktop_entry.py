"""Desktop entrypoint for the packaged IA Local Agent API sidecar."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import uvicorn

from src.config import load_dotenv


APP_NAME = "IA Local Agent"
DEFAULT_PORT = "8765"
DEFAULT_TOKEN = "local-dev-token"


def app_local_data_dir() -> Path:
    """Return a writable per-user directory for packaged desktop data."""
    base = os.getenv("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / "AppData" / "Local" / APP_NAME


def configure_environment() -> Path:
    """Prepare safe desktop defaults without overwriting explicit user config."""
    load_dotenv()

    data_root = Path(os.getenv("IA_LOCAL_AGENT_DATA_DIR", str(app_local_data_dir()))).expanduser()
    data_dir = data_root / "data"
    logs_dir = data_root / "logs"
    chroma_dir = data_root / "chroma"

    for directory in (data_root, data_dir, logs_dir, chroma_dir):
        directory.mkdir(parents=True, exist_ok=True)

    desktop_defaults = {
        "APP_ENV": "desktop",
        "API_HOST": "127.0.0.1",
        "API_PORT": DEFAULT_PORT,
        "LOCAL_API_KEY": DEFAULT_TOKEN,
        "API_ALLOWED_ORIGINS": "http://127.0.0.1:1420,http://localhost:1420,tauri://localhost,http://tauri.localhost",
        "API_EXPOSE_DOCS": "false",
        "API_DEV_MODE": "false",
        "SETTINGS_ENV_PATH": str(data_root / ".env"),
        "CONVERSATIONS_PATH": str(data_root / "conversations.sqlite3"),
        "CHROMA_PATH": str(chroma_dir),
        "RAG_MANIFEST_PATH": str(data_root / "rag_manifest.json"),
        "TOOL_AUDIT_LOG_PATH": str(logs_dir / "tool_audit.jsonl"),
        "AGENT_TIMING_LOG_PATH": str(logs_dir / "agent_timing.jsonl"),
        "LOG_LEVEL": "INFO",
    }

    for key, value in desktop_defaults.items():
        os.environ.setdefault(key, value)

    os.environ["API_HOST"] = "127.0.0.1"
    if os.environ.get("API_PORT") in {None, ""}:
        os.environ["API_PORT"] = DEFAULT_PORT

    return logs_dir


def configure_logging(logs_dir: Path) -> None:
    log_path = logs_dir / "api.log"
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def main() -> int:
    logs_dir = configure_environment()
    configure_logging(logs_dir)

    from src.api.app import app
    from src.api.config import get_api_settings

    settings = get_api_settings()
    if settings.host != "127.0.0.1":
        logging.warning("Desktop mode refused non-loopback API_HOST=%s", settings.host)

    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=settings.port,
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
            log_config=None,
            access_log=False,
        )
    except Exception:
        logging.exception("Desktop API failed to start")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
