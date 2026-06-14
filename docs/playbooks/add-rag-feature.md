# Playbook: Anadir Feature RAG

## Objetivo

Mejorar ingestion, busqueda, fuentes, manifest, seguridad o UI del RAG local.

## Repositorio

Proyecto:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Pasos

1. Leer `docs/RAG_ARCHITECTURE.md`.
2. Identificar componente:

```text
src/rag/loaders.py
src/rag/processing.py
src/rag/security.py
src/rag/chunking.py
src/rag/store.py
src/rag/manifest.py
src/rag/service.py
```

3. Mantener ingestion dentro de `RAG_DOCUMENTS_ROOT`.
4. Respetar `.ragignore` y scanner de secretos.
5. Mantener `safe_source` para respuestas/UI.
6. Actualizar endpoints en `src/api/routes/memory.py` si aplica.
7. Actualizar panel UI si cambia estado, fuentes o documentos.
8. Anadir tests.

## Pruebas

```powershell
venv\Scripts\python.exe -m pytest tests\e2e\test_05_semantic_memory.py
venv\Scripts\python.exe -m pytest tests\e2e\test_13_rag_basic.py
venv\Scripts\python.exe -m pytest tests\e2e\test_14_secret_exposure.py
venv\Scripts\python.exe -m pytest tests\api\test_api.py
```

Si afecta UI:

```powershell
cd ui\desktop
npm run build
```

## Agentes

- `rag-memory-agent.md`
- `backend-api-agent.md`
- `frontend-tauri-agent.md` si hay panel UI
- `qa-test-agent.md`
