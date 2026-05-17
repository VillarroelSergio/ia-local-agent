# IA Local Agent

Agente IA local para Windows usando modelos open source servidos desde LM Studio y una interfaz Python por consola.

La meta es evolucionar desde un chat local hacia un copiloto privado para Windows: con tools, memoria, RAG local, automatizacion, voz y UI propia.

## Estado Actual

- Chat local con LM Studio mediante API compatible con OpenAI.
- Streaming de respuestas en consola.
- Historial persistente en SQLite.
- Tool calling automatico con confirmacion del usuario.
- Tools manuales desde consola.
- Memoria persistente y semantica con ChromaDB.
- Embeddings locales reales con `sentence-transformers`.
- Gestion de memoria largo plazo: recuerdos explicitos, busqueda, estadisticas y reindexado.
- Backend modular: providers, prompts, contexto, conversaciones, memoria, tools y orquestacion inicial.

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
|   |-- tools.py             # Fachada de tools
|   |-- tooling/             # Registry, permisos, auditoria, ejecucion
|   |-- tools_catalog/       # Catalogo de tools locales
|   `-- orchestration/       # Workflows agenticos iniciales
|-- ui/
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
sentence-transformers
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

- Por defecto usa `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Si `sentence-transformers` o el modelo no estan disponibles, cae al embedding hash local para mantener el agente operativo.
- Al cambiar de embedding, ejecuta `/memory_rebuild` para reindexar el historial guardado.

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
CONVERSATIONS_PATH=data/conversations.sqlite3
CHROMA_PATH=data/chroma
SEMANTIC_MEMORY_ENABLED=true
SEMANTIC_MEMORY_RESULTS=5
SEMANTIC_EMBEDDING_PROVIDER=auto
SEMANTIC_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
LONG_TERM_MEMORY_ENABLED=true
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
- `tooling/`: registry, permisos, auditoria y ejecucion de tools.
- `tools_catalog/`: definiciones de tools locales por dominio.
- `orchestration/`: esqueleto para workflows agenticos.
- `agent.py`: orquestador del turno conversacional.
- `cli.py`: entrada de consola.

## Roadmap

1. Mejorar seguridad y permisos de tools. En progreso: registry, permisos y auditoria ya separados.
2. Crear memoria persistente. Hecho: SQLite para conversaciones y ChromaDB para memoria.
3. Mejorar memoria con busqueda semantica. Hecho base: embeddings locales reales, busqueda y reindexado.
4. Anadir RAG local sobre documentos.
5. Integrar embeddings locales. Hecho base con `sentence-transformers`.
6. Automatizacion Windows avanzada.
7. UI propia.
8. Voz local con STT y TTS.

## Filosofia

Este proyecto no busca ser solo un chat local. La meta es construir un Jarvis/Copilot privado para Windows, capaz de ayudar en desarrollo, controlar herramientas reales, recordar contexto y funcionar de forma local.
