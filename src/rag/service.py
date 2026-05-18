"""Servicio RAG local: ingestion, busqueda y formateo con fuentes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import monotonic

from .chunking import ChunkingService
from .loaders import DocumentLoaderRegistry
from .manifest import DocumentManifest
from .models import RagSearchResult
from .processing import DocumentProcessor, sha256_file
from .security import find_secret_markers, is_ignored, load_ignore_patterns, relative_posix
from .store import ChromaRagStore


class LocalRagService:
    """Facade principal del RAG documental."""

    def __init__(self, settings):
        self.settings = settings
        self.project_root = settings.project_root
        self.allowed_root = Path(settings.rag_documents_root).resolve()
        self.manifest = DocumentManifest(settings.rag_manifest_path)
        self.loaders = DocumentLoaderRegistry()
        self.processor = DocumentProcessor(self.project_root)
        self.chunker = ChunkingService(
            target_tokens=settings.rag_chunk_tokens,
            overlap_tokens=settings.rag_chunk_overlap_tokens,
        )
        self.store = ChromaRagStore(
            settings.chroma_path,
            embedding_provider=settings.rag_embedding_provider,
            embedding_model=settings.rag_embedding_model,
            embedding_base_url=settings.lmstudio_base_url,
            embedding_api_key=settings.lmstudio_api_key,
        )

    def index_path(self, path: str | Path, *, project_id: str = "default", force=False) -> dict:
        root = Path(path).expanduser().resolve()

        if not self._is_allowed(root):
            return {"error": f"Ruta fuera de RAG_DOCUMENTS_ROOT: {root}"}

        if not root.exists():
            return {"error": f"La ruta no existe: {root}"}

        started_at = monotonic()
        files = self._discover_files(root)
        report = {
            "path": str(root),
            "project_id": project_id,
            "discovered": len(files),
            "indexed": 0,
            "skipped": 0,
            "blocked": 0,
            "errors": [],
        }

        for file_path in files:
            result = self.index_file(file_path, project_id=project_id, force=force)

            if result.get("indexed"):
                report["indexed"] += 1
            elif result.get("blocked"):
                report["blocked"] += 1
            elif result.get("error"):
                report["errors"].append(result)
            else:
                report["skipped"] += 1

        report["duration_ms"] = int((monotonic() - started_at) * 1000)
        return report

    def index_file(self, path: str | Path, *, project_id: str = "default", force=False) -> dict:
        file_path = Path(path).expanduser().resolve()

        if not self._is_allowed(file_path):
            return {"error": f"Ruta fuera de RAG_DOCUMENTS_ROOT: {file_path}"}

        if not self.loaders.supports(file_path):
            return {"skipped": True, "reason": "unsupported_type", "path": str(file_path)}

        try:
            content_hash = sha256_file(file_path)
            source_path = str(file_path)
            existing = self.manifest.get(source_path) or {}
            current_embedding = self.store.embedding_function.name()
            same_content = existing.get("content_hash") == content_hash
            same_embedding = existing.get("embedding") == current_embedding
            changed = not (same_content and same_embedding)
            version = int(existing.get("version", 0)) + 1 if changed else int(existing.get("version", 1))

            if not changed and not force:
                return {"skipped": True, "reason": "unchanged", "path": str(file_path)}

            raw = self.loaders.load(file_path)
            secret_markers = find_secret_markers(raw.text)

            if secret_markers:
                return {
                    "blocked": True,
                    "reason": "secret_markers_detected",
                    "path": str(file_path),
                    "markers": secret_markers,
                }

            document = self.processor.process(raw, version=version)
            document.metadata["project_id"] = project_id
            chunks = self.chunker.chunk(document)
            self.store.delete_by_doc_id(document.doc_id)
            self.store.upsert_chunks(chunks)
            self.manifest.update(source_path, {
                "doc_id": document.doc_id,
                "source_path": source_path,
                "safe_source": relative_posix(file_path, self.project_root),
                "content_hash": content_hash,
                "version": version,
                "chunk_count": len(chunks),
                "project_id": project_id,
                "file_type": document.file_type,
                "embedding": current_embedding,
                "indexed_at": datetime.now().isoformat(timespec="seconds"),
            })
            return {
                "indexed": True,
                "path": str(file_path),
                "doc_id": document.doc_id,
                "version": version,
                "chunks": len(chunks),
            }
        except Exception as error:
            return {"error": str(error), "path": str(file_path)}

    def search(
        self,
        query: str,
        *,
        project_id: str | None = None,
        file_type: str | None = None,
        source: str | None = None,
        top_k: int | None = None,
    ) -> RagSearchResult:
        filters = {}

        if project_id:
            filters["project_id"] = project_id
        if file_type:
            filters["file_type"] = file_type
        if source:
            filters["safe_source"] = source

        chunks, trace = self.store.search(
            query,
            top_k=top_k or self.settings.rag_top_k,
            filters=filters,
        )
        trace.update({
            "query_original": query,
            "top_k": top_k or self.settings.rag_top_k,
            "selected_chunks": [
                {
                    "chunk_id": chunk.id,
                    "distance": chunk.distance,
                    "source": chunk.metadata.get("safe_source"),
                    "heading_path": chunk.metadata.get("heading_path"),
                    "page_start": chunk.metadata.get("page_start"),
                }
                for chunk in chunks
            ],
        })
        return RagSearchResult(query=query, chunks=chunks, trace=trace)

    def format_context(self, result: RagSearchResult, *, max_chars=12000) -> str:
        if not result.chunks:
            return "No se encontro contexto relevante en la documentacion local."

        sections = []
        used = 0

        for index, chunk in enumerate(result.chunks, start=1):
            metadata = chunk.metadata
            source = metadata.get("safe_source", metadata.get("file_name", "documento"))
            heading = metadata.get("heading_path") or metadata.get("symbol_name") or ""
            page = metadata.get("page_start")
            location = f"{source}"

            if heading:
                location += f" | {heading}"
            if page:
                location += f" | pagina {page}"

            block = f"[Fuente {index}: {location}]\n{chunk.content}"

            if used + len(block) > max_chars:
                break

            sections.append(block)
            used += len(block)

        return "\n\n".join(sections)

    def stats(self) -> dict:
        return {
            "documents": len(self.manifest.items),
            "chunks": self.store.collection.count(),
            "collection": self.store.collection.name,
            "embedding": self.store.embedding_function.name(),
            "documents_root": str(self.allowed_root),
        }

    def _discover_files(self, root: Path) -> list[Path]:
        patterns = load_ignore_patterns(self.project_root)

        if root.is_file():
            return [root] if self.loaders.supports(root) and not is_ignored(root, self.project_root, patterns) else []

        files = []

        for path in root.rglob("*"):
            if path.is_file() and self.loaders.supports(path) and not is_ignored(path, self.project_root, patterns):
                files.append(path)

        return files

    def _is_allowed(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.allowed_root)
            return True
        except ValueError:
            return False
