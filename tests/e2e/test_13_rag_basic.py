from src.rag import LocalRagService


def test_rag_ingests_markdown_and_retrieves_relevant_chunk(test_settings, sandbox):
    document = sandbox / "project.md"
    document.write_text(
        "# Proyecto IA Local\n"
        "Este agente usa memoria semántica, tools y LM Studio.\n",
        encoding="utf-8",
    )
    service = LocalRagService(test_settings)

    report = service.index_path(document, project_id="e2e", force=True)
    result = service.search("Qué usa el agente?", project_id="e2e", top_k=3)
    context = service.format_context(result)

    assert report["indexed"] == 1
    assert service.stats()["chunks"] >= 1
    assert "memoria semántica, tools y LM Studio" in context
