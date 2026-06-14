# RAG Memory Agent

## Mision

Mejorar memoria semantica, RAG local, ingestion, retrieval, manifest, fuentes y panel visual de memoria sin exponer secretos ni rutas privadas innecesarias.

## Repositorio

Trabaja sobre el workspace de `https://github.com/VillarroelSergio/ia-local-agent.git`.

## Leer Primero

- `AGENT.md`
- `README.md`
- `docs/RAG_ARCHITECTURE.md`
- `src/rag/`
- `src/semantic_memory.py`
- `src/tools_catalog/rag.py`
- `src/api/routes/memory.py`
- `src/api/services/memory_service.py`
- `ui/desktop/src/features/settings/MemoryStatus.tsx`
- `ui/desktop/src/features/settings/SettingsModal.tsx`

## Responsabilidades

- Mantener ingestion dentro de `RAG_DOCUMENTS_ROOT`.
- Respetar `.ragignore`, bloqueos de carpetas sensibles y scanner de secretos.
- Usar `safe_source` para UI y respuestas.
- Mejorar atribucion de fuentes, stats, documentos indexados, borrado y reindexado.
- Mantener separacion entre memoria conversacional, RAG documental y auditoria.
- Permitir modo de desarrollo con `SEMANTIC_EMBEDDING_PROVIDER=local_hash`.

## Validaciones

```powershell
venv\Scripts\python.exe -m pytest tests\e2e\test_05_semantic_memory.py
venv\Scripts\python.exe -m pytest tests\e2e\test_13_rag_basic.py
venv\Scripts\python.exe -m pytest tests\api\test_api.py
```

Comprobaciones manuales:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/memory/stats
```

## Riesgos

- Indexar `.env`, credenciales, perfiles de navegador o AppData.
- Mostrar rutas absolutas sensibles en UI.
- Romper manifest incremental y duplicar documentos.
- Cambiar embeddings sin migracion o limpieza de Chroma.

## Criterio De Salida

La ingestion y busqueda son reproducibles, no filtran secretos, y la UI puede mostrar estado/fuentes de forma segura.
