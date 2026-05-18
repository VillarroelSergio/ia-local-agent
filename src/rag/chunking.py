"""Chunking por tipo documental."""

from __future__ import annotations

import hashlib
import re

from .models import Chunk, ProcessedDocument


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
PY_SYMBOL_RE = re.compile(r"^(class|def|async def)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)


def approximate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


def stable_chunk_id(doc_id: str, version: int, index: int, text: str) -> str:
    digest = hashlib.sha256(f"{doc_id}:{version}:{index}:{text}".encode("utf-8")).hexdigest()
    return digest[:32]


class ChunkingService:
    """Divide documentos preservando estructura semantica cuando existe."""

    def __init__(self, target_tokens=750, overlap_tokens=120):
        self.target_chars = target_tokens * 4
        self.overlap_chars = overlap_tokens * 4

    def chunk(self, document: ProcessedDocument) -> list[Chunk]:
        if document.file_type == "markdown":
            parts = self._split_markdown(document.text)
        elif document.file_type == "code":
            parts = self._split_code(document.text)
        elif document.file_type == "pdf":
            parts = self._split_pdf(document.text)
        else:
            parts = [("", document.text, {})]

        chunks = []
        chunk_index = 0

        for heading_path, text, extra_metadata in parts:
            for piece in self._split_large_text(text):
                clean_piece = piece.strip()

                if not clean_piece:
                    continue

                metadata = {
                    **document.metadata,
                    **extra_metadata,
                    "chunk_index": chunk_index,
                    "heading_path": heading_path,
                    "token_count": approximate_tokens(clean_piece),
                }
                embedding_text = self._embedding_text(document, heading_path, clean_piece)
                chunks.append(Chunk(
                    id=stable_chunk_id(document.doc_id, document.version, chunk_index, clean_piece),
                    doc_id=document.doc_id,
                    text=clean_piece,
                    embedding_text=embedding_text,
                    metadata=metadata,
                ))
                chunk_index += 1

        return chunks

    def _embedding_text(self, document: ProcessedDocument, heading_path: str, text: str) -> str:
        title = document.metadata.get("safe_source", document.path.name)
        section = f"\nSection: {heading_path}" if heading_path else ""
        return f"Document: {title}{section}\nType: {document.file_type}\n\n{text}"

    def _split_large_text(self, text: str) -> list[str]:
        if len(text) <= self.target_chars:
            return [text]

        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current = ""

        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph

            if len(candidate) <= self.target_chars:
                current = candidate
                continue

            if current:
                chunks.append(current)
                current = self._overlap_tail(current)

            if len(paragraph) > self.target_chars:
                chunks.extend(self._split_by_window(paragraph))
                current = ""
            else:
                current = f"{current}\n\n{paragraph}".strip() if current else paragraph

        if current:
            chunks.append(current)

        return chunks

    def _split_by_window(self, text: str) -> list[str]:
        chunks = []
        start = 0

        while start < len(text):
            end = min(len(text), start + self.target_chars)
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = max(end - self.overlap_chars, start + 1)

        return chunks

    def _overlap_tail(self, text: str) -> str:
        if self.overlap_chars <= 0:
            return ""

        return text[-self.overlap_chars:]

    def _split_markdown(self, text: str) -> list[tuple[str, str, dict]]:
        sections = []
        heading_stack: list[tuple[int, str]] = []
        current_lines = []
        current_heading = ""

        for line in text.splitlines():
            match = HEADING_RE.match(line)

            if match:
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines), {}))
                    current_lines = []

                level = len(match.group(1))
                title = match.group(2).strip()
                heading_stack = [
                    (item_level, item_title)
                    for item_level, item_title in heading_stack
                    if item_level < level
                ]
                heading_stack.append((level, title))
                current_heading = " > ".join(item_title for _, item_title in heading_stack)

            current_lines.append(line)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines), {}))

        return sections or [("", text, {})]

    def _split_pdf(self, text: str) -> list[tuple[str, str, dict]]:
        parts = re.split(r"\n\[Page (\d+)\]\n", text)

        if len(parts) <= 1:
            return [("", text, {})]

        sections = []
        for index in range(1, len(parts), 2):
            page = int(parts[index])
            page_text = parts[index + 1]
            sections.append((f"Page {page}", page_text, {"page_start": page, "page_end": page}))

        return sections

    def _split_code(self, text: str) -> list[tuple[str, str, dict]]:
        matches = list(PY_SYMBOL_RE.finditer(text))

        if not matches:
            return [("", text, {})]

        sections = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            symbol_type = match.group(1)
            symbol_name = match.group(2)
            sections.append((
                symbol_name,
                text[start:end],
                {"symbol_type": symbol_type, "symbol_name": symbol_name},
            ))

        prefix = text[:matches[0].start()].strip()
        if prefix:
            sections.insert(0, ("module", prefix, {"symbol_type": "module", "symbol_name": "module"}))

        return sections
