"""Normalizacion, metadata y fingerprinting documental."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

from .models import ProcessedDocument, RawDocument
from .security import relative_posix


WHITESPACE_RE = re.compile(r"[ \t]+")
BLANK_LINES_RE = re.compile(r"\n{4,}")


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def normalize_text(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(WHITESPACE_RE.sub(" ", line).rstrip() for line in normalized.split("\n"))
    return BLANK_LINES_RE.sub("\n\n\n", normalized).strip()


class DocumentProcessor:
    """Convierte documentos crudos en documentos versionados."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def process(self, raw: RawDocument, *, version: int) -> ProcessedDocument:
        stat = raw.path.stat()
        text = normalize_text(raw.text)
        content_hash = sha256_file(raw.path)
        doc_id = sha256_text(str(raw.path.resolve()).lower())[:24]
        metadata = {
            **raw.metadata,
            "doc_id": doc_id,
            "source_path": str(raw.path.resolve()),
            "safe_source": relative_posix(raw.path, self.project_root),
            "file_name": raw.path.name,
            "file_type": raw.file_type,
            "file_size": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "indexed_at": datetime.now().isoformat(timespec="seconds"),
            "version": version,
            "content_hash": content_hash,
        }
        return ProcessedDocument(
            doc_id=doc_id,
            path=raw.path,
            text=text,
            file_type=raw.file_type,
            version=version,
            content_hash=content_hash,
            metadata=metadata,
        )
