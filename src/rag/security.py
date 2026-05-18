"""Seguridad local para indexacion documental."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path


DEFAULT_IGNORE_PATTERNS = [
    ".git/**",
    "*/.git/**",
    "venv/**",
    "*/venv/**",
    ".venv/**",
    "*/.venv/**",
    "__pycache__/**",
    "*/__pycache__/**",
    "node_modules/**",
    "*/node_modules/**",
    "data/chroma/**",
    "*/data/chroma/**",
    "data/hf_cache/**",
    "*/data/hf_cache/**",
    "*/data/*.sqlite3",
    "*.sqlite",
    "*.sqlite3",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "token.json",
    "secrets.*",
]

SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*['\"]?[^'\"\s]{12,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bBearer\s+[a-z0-9._\-]{20,}"),
]


def load_ignore_patterns(root: Path) -> list[str]:
    ignore_file = root / ".ragignore"
    patterns = list(DEFAULT_IGNORE_PATTERNS)

    if ignore_file.exists():
        for raw_line in ignore_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)

    return patterns


def relative_posix(path: Path, root: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return path.name

    return relative.as_posix()


def is_ignored(path: Path, root: Path, patterns: list[str]) -> bool:
    relative = relative_posix(path, root)

    for pattern in patterns:
        normalized = pattern.replace("\\", "/")
        if fnmatch.fnmatch(relative, normalized) or fnmatch.fnmatch(path.name, normalized):
            return True

    return False


def find_secret_markers(text: str) -> list[str]:
    markers = []

    for pattern in SECRET_PATTERNS:
        if pattern.search(text or ""):
            markers.append(pattern.pattern)

    return markers
