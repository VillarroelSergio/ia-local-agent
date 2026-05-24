# IA Local Agent

Agente IA local para Windows usando modelos open source servidos desde LM Studio, backend FastAPI local-first y una interfaz desktop Tauri + React.

La meta es evolucionar desde un chat local hacia un copiloto privado para Windows: con tools, memoria, RAG local, automatizacion, voz y UI propia.

## Estado Actual

- Chat local con LM Studio mediante API compatible con OpenAI.
- Streaming de respuestas en consola.
- Historial persistente en SQLite.
- Tool calling automatico con confirmacion del usuario.
- Tools manuales desde consola.
- Memoria persistente y semantica con ChromaDB.
- Embeddings locales via LM Studio para memoria y RAG.
- Gestion de memoria largo plazo: recuerdos explicitos, busqueda, estadisticas y reindexado.
- RAG local documental sobre ChromaDB para Markdown, TXT, JSON, CSV, codigo y PDFs.
- Backend modular: providers, prompts, contexto, conversaciones, memoria, tools y orquestacion inicial.
- Desktop App MVP con Tauri + React en `ui/desktop`, conectada a la API local.
- Build Windows con backend Python empaquetado como sidecar Tauri.

## Estructura

```text
ia-local-agent/
|-- data/                    # Datos locales ignorados por Git
|-- docs/
|-- rag/
|-- src/
|   |-- agent.py             # Orquestador principal
|   |-- cli.py               # Entrada CLI
|   |-- config.py            # Configuracion
|   |-- context.py           # Construccion y recorte de contexto
|   |-- conversations.py     # SQLite e historial
|   |-- prompts.py           # System prompt
|   |-- providers.py         # Providers LLM
|   |-- semantic_memory.py   # ChromaDB + embeddings
|   |-- rag/                 # Ingestion, chunking, ChromaDB y retrieval documental
|   |-- tools.py             # Fachada de tools
|   |-- tooling/             # Registry, permisos, auditoria, ejecucion
|   |-- tools_catalog/       # Catalogo de tools locales
|   `-- orchestration/       # Workflows agenticos iniciales
|-- ui/
|   `-- desktop/             # Tauri + React desktop MVP
|-- requirements.txt
`-- README.md
```

## Requisitos

- Windows.
- Python.
- LM Studio con servidor local activado.
- Un modelo cargado en LM Studio.

Dependencias principales:

```text
openai
psutil
chromadb
pypdf
```

Instalacion:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Nota: existe una carpeta antigua llamada `requeriments.txt`; las dependencias actuales viven en `requirements.txt`.

## Configuracion LM Studio

Servidor local:

```text
http://127.0.0.1:1234
```

Base URL OpenAI-compatible:

```text
http://127.0.0.1:1234/v1
```

Configuracion recomendada:

```text
Modelo: Qwen3.5 9B Q4_K_M
Context Length: 4096
GPU Offload: MAX
Flash Attention: ON si esta disponible
Batch Size: 512-1024
```

## Ejecutar

Desde la raiz del proyecto:

```powershell
venv\Scripts\python.exe src\cli.py
```

Entrada equivalente:

```powershell
venv\Scripts\python.exe src\agent.py
```

Para salir:

```text
salir
```

## Desktop App MVP

La UI desktop vive en `ui/desktop` y consume exclusivamente la API FastAPI local.

Modo desarrollo: primero arranca el backend:

```powershell
python -m src.api.main
```

Luego, desde `ui\desktop`:

```powershell
npm install
npm run tauri:dev
```

Modo app Windows instalable:

```powershell
.\scripts\build-windows-app.ps1
```

Resultado esperado:

```text
ui\desktop\src-tauri\target\release\bundle\nsis\IA Local Agent Setup.exe
```

O:

```text
ui\desktop\src-tauri\target\release\bundle\msi\IA Local Agent.msi
```

En modo empaquetado, Tauri arranca automaticamente el backend FastAPI como sidecar en `127.0.0.1:8765`, verifica `/api/health`, reutiliza un backend sano si ya existe y cierra el proceso creado por Tauri al salir.

Detalles completos: [docs/DESKTOP_APP_MVP.md](docs/DESKTOP_APP_MVP.md).

Guia de build Windows: [docs/WINDOWS_APP_BUILD.md](docs/WINDOWS_APP_BUILD.md).

## Uso Basico

Puedes chatear normalmente:

```text
Tu: resume que puedes hacer
```

El modelo puede pedir ejecutar una tool. Antes de hacerlo, el agente pedira confirmacion:

```text
El modelo quiere ejecutar 'get_system_info' con argumentos:
{}
Confirmar? (s/n):
```

Solo se ejecuta si respondes `s`, `si`, `y` o `yes`.

## Memoria

La memoria local usa:

- SQLite para historial conversacional: `data/conversations.sqlite3`
- ChromaDB para memoria semantica: `data/chroma/`
- Cache local del modelo de embeddings: `data/hf_cache/`

Estos datos estan ignorados por Git porque pueden contener informacion privada.

En modo app Windows empaquetada, los datos modificables se redirigen a:

```text
C:\Users\<usuario>\AppData\Local\IA Local Agent\
```

para evitar escritura dentro de `Program Files`.

Comandos:

```text
/remember El usuario prefiere respuestas breves en espanol.
/memories
/memory_search preferencias del usuario
/memory_stats
/memory_rebuild
/forget id_de_memoria
```

Flujo de memoria:

```text
Usuario pregunta algo
-> Se busca memoria relevante en ChromaDB
-> Se carga historial reciente desde SQLite
-> Todo se inyecta en el prompt
-> LM Studio responde con mas contexto
```

Embeddings:

- Por defecto usa LM Studio con `text-embedding-nomic-embed-text-v1.5`.
- Si prefieres `sentence-transformers`, configura `SEMANTIC_EMBEDDING_PROVIDER=sentence-transformers`.
- Al cambiar de embedding, ejecuta `/memory_rebuild` para reindexar el historial guardado.

## RAG Local

El RAG documental usa ChromaDB persistente, manifest incremental en `data/rag_manifest.json` y `.ragignore` para excluir secretos, entornos virtuales, caches y datos privados. Por defecto genera embeddings contra LM Studio usando el modelo `text-embedding-nomic-embed-text-v1.5`.

Comandos:

```text
/rag_index README.md --project selftest
/rag_index docs --project local-agent
/rag_search como ejecuto el agente
/rag_stats
```

La tool `search_local_knowledge` queda disponible para el modelo cuando la pregunta dependa de documentacion local indexada. Devuelve contexto con fuentes, distancias y metadata.

Tipos soportados:

| Tipo | Estrategia |
| --- | --- |
| Markdown | Chunking por jerarquia de headings |
| TXT/log | Chunking por parrafos con overlap |
| JSON | Pretty-print estructurado antes de chunking |
| CSV | Filas convertidas a texto con columnas |
| Codigo | Chunking por simbolos Python cuando aplica, fallback por texto |
| PDF | Extraccion por paginas con `pypdf` |

## Tools

Las tools estan registradas mediante `ToolRegistry` y se exponen al modelo con schemas OpenAI-compatible. Tambien pueden ejecutarse manualmente desde consola:

```text
/tool notepad
/tool calc
/tool sistema
/tool get_running_processes {"limit": 10}
/tool search_files {"path": ".", "pattern": "*.md", "limit": 5}
/tool run_powershell {"command": "Get-Date"}
/tool list_directory {"path": ".", "limit": 20}
/tool read_text_file {"path": "README.md", "max_chars": 2000}
/tool get_clipboard
/tool set_clipboard {"text": "hola desde el agente"}
/tool open_url {"url": "https://example.com"}
/tool search_local_knowledge {"query": "como se ejecuta el agente", "project_id": "selftest", "top_k": 3}
```

Tools disponibles:

| Tool | Uso |
| --- | --- |
| `open_notepad` | Abre el Bloc de notas |
| `open_calculator` | Abre la calculadora |
| `open_application` | Abre apps permitidas por allowlist |
| `get_system_info` | Muestra informacion basica del sistema |
| `get_running_processes` | Lista procesos activos |
| `search_files` | Busca archivos por patron |
| `list_directory` | Lista archivos y carpetas |
| `read_text_file` | Lee archivos de texto UTF-8 |
| `get_clipboard` | Lee el portapapeles |
| `set_clipboard` | Escribe en el portapapeles |
| `get_mouse_position` | Devuelve posicion del raton |
| `get_screen_size` | Devuelve tamano de pantalla |
| `move_mouse` | Mueve el raton |
| `click_mouse` | Hace click |
| `press_key` | Pulsa una tecla |
| `hotkey` | Pulsa combinaciones de teclas |
| `type_text` | Escribe texto |
| `open_url` | Abre una URL |
| `run_powershell` | Ejecuta comandos PowerShell permitidos |
| `search_local_knowledge` | Busca contexto en la documentacion local indexada |

Apps permitidas en `open_application`:

```text
notepad
calculator
explorer
paint
cmd
powershell
```

Comandos permitidos en `run_powershell`:

```text
Get-Date
Get-Process
Get-Service
Get-ComputerInfo
Get-ChildItem
Test-Path
Where-Object
Select-Object
Sort-Object
Measure-Object
Format-Table
Format-List
```

Por seguridad se bloquean tokens de composicion o redireccion como `;`, `&&`, `||`, `$(`, backticks, `>`, `>>` y `<`.

Limites principales:

| Recurso | Limite |
| --- | --- |
| PowerShell timeout | 15 segundos |
| PowerShell command | 300 caracteres |
| `get_running_processes` | 50 procesos |
| `search_files` | 100 resultados |
| `list_directory` | 100 elementos |
| `read_text_file` | 12000 caracteres |
| Clipboard | 8000 caracteres |
| `type_text` | 500 caracteres |
| `click_mouse` | 3 clicks |

## Configuracion

Variables `.env` soportadas:

```text
APP_ENV=dev
DEFAULT_PROVIDER=lmstudio
DEFAULT_MODEL=qwen/qwen3.5-9b
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_API_KEY=lm-studio
LLM_TEMPERATURE=0.7
MAX_CONTEXT_TOKENS=4096
RESERVED_RESPONSE_TOKENS=1024
TOOLS_REQUIRE_CONFIRMATION=true
TOOL_ALLOWED_ROOTS=D:\local-ai-agent\project
TOOL_CONFIRM_READ_ROOTS=D:\;C:\Users\Sergio Villa\Documents;C:\Users\Sergio Villa\Desktop;C:\Users\Sergio Villa\Downloads;C:\Users\Sergio Villa\Pictures;C:\Users\Sergio Villa\Videos
CONVERSATIONS_PATH=data/conversations.sqlite3
CHROMA_PATH=data/chroma
SEMANTIC_MEMORY_ENABLED=true
SEMANTIC_MEMORY_RESULTS=5
SEMANTIC_EMBEDDING_PROVIDER=lmstudio
SEMANTIC_EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5
LONG_TERM_MEMORY_ENABLED=true
RAG_DOCUMENTS_ROOT=..
RAG_MANIFEST_PATH=data/rag_manifest.json
RAG_EMBEDDING_PROVIDER=lmstudio
RAG_EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5
RAG_CHUNK_TOKENS=750
RAG_CHUNK_OVERLAP_TOKENS=120
RAG_TOP_K=8
LOG_LEVEL=INFO
```

## Arquitectura

```text
CLI / futura UI
    -> LocalAgent
        -> ContextBuilder
        -> PromptManager
        -> ConversationManager
        -> SemanticMemoryManager
        -> LocalRagService / ChromaRagStore
        -> ProviderRegistry / LLMProvider
        -> ToolRegistry / ToolExecutor
```

Modulos principales:

- `config.py`: configuracion desde `.env` y variables de entorno.
- `providers.py`: interfaz `LLMProvider`, `LMStudioProvider` y registro de providers.
- `prompts.py`: renderizado del system prompt.
- `conversations.py`: mensajes, conversaciones y persistencia SQLite.
- `context.py`: recorte de contexto e inyeccion de memoria.
- `semantic_memory.py`: memoria semantica sobre ChromaDB.
- `rag/`: RAG documental local con loaders, manifest incremental, chunking, ChromaDB y retrieval.
- `tooling/`: registry, permisos, auditoria y ejecucion de tools.
- `tools_catalog/`: definiciones de tools locales por dominio.
- `orchestration/`: esqueleto para workflows agenticos.
- `agent.py`: orquestador del turno conversacional.
- `cli.py`: entrada de consola.

## Roadmap

1. Mejorar seguridad y permisos de tools. En progreso: registry, permisos y auditoria ya separados.
2. Crear memoria persistente. Hecho: SQLite para conversaciones y ChromaDB para memoria.
3. Mejorar memoria con busqueda semantica. Hecho base: embeddings locales por LM Studio, busqueda y reindexado.
4. Anadir RAG local sobre documentos. Hecho base: ingestion, chunking, ChromaDB, CLI y tool.
5. Integrar embeddings locales. Hecho base con LM Studio y fallback opcional a `sentence-transformers`.
6. Automatizacion Windows avanzada.
7. UI propia.
8. Voz local con STT y TTS.

## Filosofia

Este proyecto no busca ser solo un chat local. La meta es construir un Jarvis/Copilot privado para Windows, capaz de ayudar en desarrollo, controlar herramientas reales, recordar contexto y funcionar de forma local.
