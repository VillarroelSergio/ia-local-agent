"""Tools RAG para consultar documentacion local."""

from __future__ import annotations

from pydantic import BaseModel, Field

try:
    from config import get_settings
    from rag import LocalRagService
    from tooling import RiskLevel, ToolContext, ToolDefinition, ToolMetadata
except ModuleNotFoundError:
    from src.config import get_settings
    from src.rag import LocalRagService
    from src.tooling import RiskLevel, ToolContext, ToolDefinition, ToolMetadata


class LocalKnowledgeSearchInput(BaseModel):
    query: str = Field(..., min_length=2, description="Pregunta o busqueda semantica.")
    project_id: str | None = Field(default=None, description="Proyecto a filtrar.")
    file_type: str | None = Field(default=None, description="markdown, pdf, text, json, csv o code.")
    source: str | None = Field(default=None, description="Ruta segura relativa exacta si se conoce.")
    top_k: int = Field(default=6, ge=1, le=20, description="Numero maximo de chunks.")


def search_local_knowledge(args: LocalKnowledgeSearchInput, ctx: ToolContext):
    settings = ctx.settings or get_settings()
    service = LocalRagService(settings)
    result = service.search(
        args.query,
        project_id=args.project_id,
        file_type=args.file_type,
        source=args.source,
        top_k=args.top_k,
    )
    return {
        "query": args.query,
        "context": service.format_context(result),
        "sources": [
            {
                "chunk_id": chunk.id,
                "source": chunk.metadata.get("safe_source"),
                "heading_path": chunk.metadata.get("heading_path"),
                "page_start": chunk.metadata.get("page_start"),
                "distance": chunk.distance,
            }
            for chunk in result.chunks
        ],
        "trace": result.trace,
    }


def build_rag_tool_definitions():
    return [
        ToolDefinition(
            metadata=ToolMetadata(
                name="search_local_knowledge",
                description=(
                    "Busca contexto relevante en la documentacion local indexada. "
                    "Usala para preguntas sobre PDFs, Markdown, TXT, JSON, CSV o codigo locales."
                ),
                category="rag",
                aliases=("rag_search", "buscar_documentacion"),
                tags=("read_only", "knowledge"),
                capabilities=("rag.search",),
                risk_level=RiskLevel.READ_ONLY,
                requires_confirmation=False,
                timeout_seconds=45,
            ),
            input_schema=LocalKnowledgeSearchInput,
            handler=search_local_knowledge,
        )
    ]
