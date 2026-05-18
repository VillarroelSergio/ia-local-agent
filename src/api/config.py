"""API-specific configuration layered over the core agent settings."""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.config import env_bool, env_int, get_settings


@dataclass(frozen=True)
class ApiSettings:
    host: str = "127.0.0.1"
    port: int = 8765
    api_key: str = "local-dev-token"
    dev_mode: bool = True
    allowed_origins: tuple[str, ...] = ("http://127.0.0.1:1420", "http://localhost:1420")
    request_size_limit: int = 1_000_000
    request_timeout_seconds: int = 120
    rate_limit_per_minute: int = 120
    expose_docs: bool = True


def get_api_settings() -> ApiSettings:
    core = get_settings()
    origins = tuple(
        origin.strip()
        for origin in os.getenv(
            "API_ALLOWED_ORIGINS",
            "http://127.0.0.1:1420,http://localhost:1420",
        ).split(",")
        if origin.strip()
    )
    host = os.getenv("API_HOST", "127.0.0.1")

    if host == "0.0.0.0" and not env_bool("API_ALLOW_NETWORK", False):
        host = "127.0.0.1"

    return ApiSettings(
        host=host,
        port=env_int("API_PORT", 8765),
        api_key=os.getenv("LOCAL_API_KEY", "local-dev-token"),
        dev_mode=env_bool("API_DEV_MODE", core.app_env == "dev"),
        allowed_origins=origins,
        request_size_limit=env_int("API_REQUEST_SIZE_LIMIT", 1_000_000),
        request_timeout_seconds=env_int("API_REQUEST_TIMEOUT_SECONDS", 120),
        rate_limit_per_minute=env_int("API_RATE_LIMIT_PER_MINUTE", 120),
        expose_docs=env_bool("API_EXPOSE_DOCS", True),
    )
