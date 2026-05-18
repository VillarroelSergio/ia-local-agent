def test_semantic_memory_remember_and_search_uses_fallback(semantic_memory):
    memory = semantic_memory.remember(
        "El usuario prefiere respuestas breves en español."
    )

    results = semantic_memory.search("preferencias del usuario", max_results=3)

    assert memory["id"]
    assert results
    assert any("respuestas breves" in result.content for result in results)
    assert semantic_memory.memory_stats()["embedding"] == "local_hash_embeddings"
