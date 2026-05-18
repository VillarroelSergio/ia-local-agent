# Arquitectura RAG local

Este proyecto implementa un RAG privado y offline-first para documentacion local.

## Flujo de ingestion

```text
ruta/carpeta
  -> .ragignore + allow root
  -> loader por extension
  -> normalizacion + metadata
  -> secret scan
  -> chunking por tipo documental
  -> embeddings locales
  -> ChromaDB upsert
  -> data/rag_manifest.json
```

Loaders soportados:

- Markdown: preserva headings como `heading_path`.
- TXT/log: texto plano normalizado.
- JSON: pretty-print estructurado.
- CSV: filas convertidas a pares columna-valor.
- Codigo: chunking por simbolos Python cuando aplica.
- PDF: extraccion por pagina con `pypdf`.

## Flujo de consulta

```text
pregunta
  -> search_local_knowledge o /rag_search
  -> query embedding
  -> ChromaDB similarity search
  -> metadata filtering
  -> contexto formateado con fuentes
  -> respuesta del agente con atribucion
```

Filtros actuales:

- `project_id`
- `file_type`
- `doc_id`
- `safe_source`

## Componentes

```text
src/rag/
  loaders.py      document loaders
  processing.py   fingerprinting, normalizacion, metadata
  security.py     .ragignore y deteccion de secretos
  chunking.py     chunkers por estructura/tipo
  store.py        ChromaDB + embedding function
  manifest.py     index incremental
  service.py      facade de ingestion/search/stats
```

## Integracion agentic

El agente expone:

- Comandos manuales: `/rag_index`, `/rag_search`, `/rag_stats`.
- Tool LLM: `search_local_knowledge`.
- Prompt: instruye al modelo a usar RAG cuando la pregunta depende de documentacion local.

## Seguridad

- Solo se indexa dentro de `RAG_DOCUMENTS_ROOT`.
- `.ragignore` excluye caches, entornos virtuales, Chroma, SQLite y secretos comunes.
- Las carpetas criticas de Windows (`C:\Windows`, `System32`, `SysWOW64`, `WinSxS`, `Temp`, `Logs`) y programas globales (`C:\Program Files`, `C:\Program Files (x86)`, `C:\ProgramData`) estan bloqueadas para tools y RAG.
- El perfil sensible del usuario bajo `AppData` (`Roaming`, `Local`, `LocalLow`) esta bloqueado por contener tokens, sesiones, caches y configuraciones privadas.
- Perfiles de navegadores (`AppData\Local\Google`, `AppData\Local\Microsoft\Edge`, `AppData\Roaming\Mozilla`) estan bloqueados explicitamente para proteger cookies, sesiones, passwords y perfiles.
- Directorios y archivos de credenciales del perfil (`.ssh`, `.aws`, `.azure`, `.docker`, `.kube`, `.gnupg`, `.git-credentials`, `.npmrc`, `.pypirc`) estan bloqueados siempre.
- Secretos dentro de proyectos (`.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa`, `id_ed25519`, `credentials.json`, `token.json`, `secrets.*`) estan bloqueados incluso si el proyecto esta permitido.
- Carpetas personales (`Documents`, `Desktop`, `Downloads`, `Pictures`, `Videos`) son de solo lectura y requieren confirmacion para tools de lectura/busqueda.
- La unidad del workspace, por ejemplo `D:\`, puede usarse para busqueda/listado/lectura solo bajo confirmacion y respetando bloqueos duros de secretos y carpetas sensibles.
- El scanner bloquea archivos con patrones de API keys, tokens bearer o private keys.
- Las respuestas usan `safe_source` para evitar exponer rutas absolutas.

## Evolucion recomendada

1. Reranking local para preguntas precisas.
2. Hybrid retrieval BM25 + vector.
3. OCR opcional para PDFs escaneados.
4. Chunking AST multi-lenguaje con tree-sitter.
5. UI para gestionar documentos, trazas y reindexado.
6. Separacion multiusuario por `user_id` y permisos por documento.
