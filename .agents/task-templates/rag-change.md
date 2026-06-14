# RAG Change Template

## Objetivo

Describe el cambio en ingestion, retrieval, memoria, fuentes o UI RAG.

## Repositorio

Trabajar en:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Agentes

- Principal: `rag-memory-agent.md`
- API: `backend-api-agent.md`
- QA: `qa-test-agent.md`

## Contexto A Leer

- `docs/RAG_ARCHITECTURE.md`
- `src/rag/`
- `src/semantic_memory.py`
- `src/tools_catalog/rag.py`
- `src/api/routes/memory.py`
- `src/api/services/memory_service.py`
- `ui/desktop/src/features/settings/MemoryStatus.tsx`

## Seguridad

- Respetar `RAG_DOCUMENTS_ROOT`.
- Respetar `.ragignore`.
- Bloquear secretos y perfiles sensibles.
- Usar `safe_source` en UI/respuestas.
- No mostrar rutas absolutas innecesarias.

## Pruebas

```powershell
venv\Scripts\python.exe -m pytest tests\e2e\test_05_semantic_memory.py
venv\Scripts\python.exe -m pytest tests\e2e\test_13_rag_basic.py
venv\Scripts\python.exe -m pytest tests\api\test_api.py
```

## Criterio De Salida

La ingestion/retrieval es reproducible, no filtra secretos y la UI muestra estado o fuentes de forma segura.
