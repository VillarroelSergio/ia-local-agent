# IA Local Agent

Agente IA local para Windows usando modelos open source servidos desde LM Studio y una interfaz Python por consola.

El objetivo del proyecto es evolucionar desde un chat local simple hacia un copiloto privado con tools, memoria, RAG, automatizacion Windows, voz y UI propia.

## Estado Actual

- Chat local con LM Studio usando API compatible con OpenAI.
- Streaming de respuestas en tiempo real.
- Historial de conversacion persistido en JSON local.
- Tools manuales desde consola.
- Tool calling automatico con confirmacion del usuario antes de ejecutar acciones.
- Tools con argumentos JSON.
- Primeras integraciones Windows y sistema.
- Memoria persistente simple en JSON local.
- Arquitectura backend modular inicial con configuracion, providers, prompts, contexto y conversaciones.

## Estructura

```text
ia-local-agent/
|-- data/
|-- docs/
|-- rag/
|-- src/
|   |-- cli.py
|   |-- agent.py
|   |-- config.py
|   |-- context.py
|   |-- conversations.py
|   |-- memory.py
|   |-- prompts.py
|   |-- providers.py
|   `-- tools.py
|-- ui/
|-- venv/
`-- README.md
```

## Requisitos

- Windows.
- Python.
- LM Studio con el servidor local activado.
- Modelo cargado en LM Studio.

Librerias usadas actualmente:

```text
openai
psutil
```

Tambien estan previstas o instaladas para fases futuras:

```text
langchain
chromadb
pyautogui
```

Nota: actualmente existe una carpeta llamada `requeriments.txt`. Lo correcto para el futuro sera tener un archivo `requirements.txt`.

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
venv\Scripts\python.exe src\agent.py
```

Entrada CLI equivalente:

```powershell
venv\Scripts\python.exe src\cli.py
```

Para salir:

```text
salir
```

## Uso

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

## Tools Manuales

Tambien puedes ejecutar tools directamente desde la consola:

```text
/tool notepad
/tool calc
/tool sistema
```

Tools con argumentos:

```text
/tool get_running_processes {"limit": 10}
/tool search_files {"path": ".", "pattern": "*.md", "limit": 5}
/tool run_powershell {"command": "Get-Date"}
```

## Memoria Persistente

La memoria se guarda localmente en:

```text
data/memory.json
```

Este archivo esta ignorado por Git porque puede contener informacion privada del usuario.

Comandos disponibles:

```text
/remember El usuario prefiere respuestas breves en espanol.
/memories
/forget id_de_memoria
```

Las memorias guardadas se inyectan en el prompt del sistema al iniciar y antes de cada respuesta del modelo.

## Arquitectura Backend

El backend esta separado en capas:

```text
CLI / futura UI
    -> LocalAgent
        -> ContextBuilder
        -> PromptManager
        -> ConversationManager
        -> ProviderRegistry / LLMProvider
        -> Tools
        -> Memory
```

Modulos principales:

- `config.py`: configuracion global desde `.env` y variables de entorno.
- `providers.py`: interfaz `LLMProvider`, `LMStudioProvider` y registro de providers.
- `prompts.py`: renderizado del system prompt.
- `conversations.py`: mensajes, conversaciones y persistencia JSON.
- `context.py`: conteo aproximado de tokens y sliding window.
- `agent.py`: orquestador del turno conversacional.
- `cli.py`: entrada de consola.

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
CONVERSATIONS_PATH=data/conversations.json
MEMORY_PATH=data/memory.json
LOG_LEVEL=INFO
```

## Tools Disponibles

### open_notepad

Abre el Bloc de notas de Windows.

### open_calculator

Abre la calculadora de Windows.

### get_system_info

Devuelve informacion basica del sistema:

- version de Windows
- CPU
- nucleos e hilos
- RAM total y disponible

### get_running_processes

Lista procesos activos ordenados por uso de memoria.

Argumentos:

```json
{
  "limit": 15
}
```

### search_files

Busca archivos dentro de una carpeta usando un patron glob.

Argumentos:

```json
{
  "path": ".",
  "pattern": "*.py",
  "limit": 20
}
```

### run_powershell

Ejecuta comandos PowerShell de inspeccion permitidos por allowlist y devuelve:

- codigo de salida
- stdout
- stderr

Argumentos:

```json
{
  "command": "Get-Date",
  "timeout": 10
}
```

Por seguridad bloquea todo lo que no este permitido explicitamente.

Comandos permitidos actualmente:

- `Get-Date`
- `Get-Process`
- `Get-Service`
- `Get-ComputerInfo`
- `Get-ChildItem`
- `Test-Path`
- `Where-Object`
- `Select-Object`
- `Sort-Object`
- `Measure-Object`
- `Format-Table`
- `Format-List`

Tambien bloquea tokens de composicion o redireccion como `;`, `&&`, `||`, `$(`, backticks, `>`, `>>` y `<`.

Limites actuales:

- maximo 15 segundos por comando PowerShell
- maximo 300 caracteres por comando PowerShell
- maximo 50 procesos en `get_running_processes`
- maximo 100 resultados en `search_files`

## Roadmap

1. Mejorar seguridad y permisos de tools.
2. Crear memoria persistente.
3. Mejorar memoria con busqueda semantica.
4. Anadir RAG local sobre documentos.
5. Integrar embeddings locales.
6. Automatizacion Windows avanzada.
7. UI propia.
8. Voz local con STT y TTS.

## Filosofia

Este proyecto no busca ser solo un chat local. La meta es construir un Jarvis/Copilot privado para Windows, capaz de ayudar en desarrollo, controlar herramientas reales, recordar contexto y funcionar de forma local.
