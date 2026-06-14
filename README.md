# IA Local Agent

Agente IA local para Windows. Usa LM Studio como proveedor LLM, FastAPI como backend local-first y una app Tauri + React como interfaz desktop.

Objetivo: evolucionar de chat local a copiloto privado para Windows, con memoria, RAG, tools, overlay contextual, automatizacion segura y voz local.

## Estado Actual

El proyecto tiene una plataforma local-first funcional y se encuentra
centrado en convertir Computer Use y el overlay en una experiencia Windows
realmente util. Desktop, API, RAG y seguridad existen como base, pero el
producto todavia no completa de forma fiable el ciclo observar, actuar y
verificar sobre aplicaciones reales.

Hecho o funcional como base:

- Backend FastAPI local en `127.0.0.1:8765`.
- Chat, streaming, WebSocket y conversaciones persistentes.
- Memoria semantica y RAG local sobre ChromaDB.
- Tool calling con registry, permisos, confirmaciones y auditoria JSONL.
- Desktop App Tauri + React con chat, historial, tools, timeline, settings y memoria.
- Runtime Windows base: ventanas, capturas, OCR base, eventos, hotkeys, workflows y scheduler.
- Computer Use MVP con sesiones SQLite, API, eventos, confirmaciones y panel desktop.
- Overlay Tauri inicial con `Ctrl+Alt+Space`, ventana compacta y lectura segura de ventana activa.

Problemas conocidos:

- El overlay ya recibe el `HWND` anterior desde Tauri, pero hay que probarlo y refinarlo con apps reales.
- Si el chat devuelve `Sin contenido`, revisar conexion con LM Studio y el ID exacto del modelo.
- UI Automation selectors todavia no esta implementado.
- OCR y workflows existen como base, pero no estan cerrados como experiencia de usuario.

## Implementado En La Ultima Iteracion

- Diagnostico LM Studio en `/api/system/lmstudio` y boton `Probar LM Studio` en settings.
- Errores de provider visibles en chat, sin burbujas vacias.
- Contexto nativo inicial del overlay: Tauri emite `overlay-context` con el `HWND` anterior.
- Foco automatico del composer al abrir overlay.
- Persistencia basica de posicion/tamano del overlay en `localStorage`.
- Boton `Usar ventana` para enviar metadata de ventana como contexto.
- Boton `Leer texto` con confirmacion y solicitud OCR bajo demanda.
- Settings iniciales para overlay: habilitado, shortcut y always-on-top.
- Gestor RAG visual minimo: stats, ruta, proyecto e indexacion.
- Endpoints nuevos: `/api/system/window/{handle}`, `/api/memory/rag/stats`, `/api/memory/rag/index`.
- Selector manual de ventanas en overlay mediante `/api/system/windows`.
- Selector de modelo detectado en Settings tras `Probar LM Studio`.
- OCR desde overlay conectado a tools `focus_window` + `ocr_active_window`.
- Lista basica de documentos indexados en el panel RAG.

## Arranque Rapido

1. Arranca LM Studio.
2. Activa el servidor OpenAI-compatible en:

```text
http://127.0.0.1:1234/v1
```

3. Comprueba que `.env` apunta al modelo cargado:

```env
DEFAULT_PROVIDER=lmstudio
DEFAULT_MODEL=qwen/qwen3.5-9b
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_API_KEY=lm-studio
```

4. Backend manual desde la raiz:

```powershell
venv\Scripts\python.exe -m src.api.main
```

5. App desktop:

```powershell
cd ui\desktop
npm run tauri:dev
```

En modo Tauri, la app puede arrancar el backend empaquetado como sidecar. Si levantas el backend manualmente, asegurate de no tener otro proceso usando el puerto `8765`.

## Comprobaciones

API:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health
Invoke-RestMethod http://127.0.0.1:8765/api/status
Invoke-RestMethod http://127.0.0.1:8765/api/metrics
```

LM Studio:

```powershell
Invoke-RestMethod http://127.0.0.1:1234/v1/models
```

Chat directo:

```powershell
$body = @{ message = "Responde solo OK"; use_tools = $false; stream = $false } | ConvertTo-Json
Invoke-RestMethod `
  -Uri http://127.0.0.1:8765/api/chat `
  -Method Post `
  -ContentType "application/json" `
  -Headers @{ "x-api-key" = "local-dev-token" } `
  -Body $body
```

Tests:

```powershell
venv\Scripts\python.exe -m pytest tests\api\test_api.py
cd ui\desktop
npm run build
cd src-tauri
cargo check
```

## Overlay

Shortcut:

```text
Ctrl + Alt + Space
```

Estado actual:

- Abre/cierra una ventana Tauri compacta.
- Muestra metadata segura de una ventana activa: titulo, proceso, pid, estado y monitor.
- No captura pantalla automaticamente.
- No ejecuta OCR continuo.
- No automatiza acciones sensibles sin confirmacion.

Endpoint:

```http
GET /api/system/active-window?exclude_own=true
```

Siguiente mejora necesaria: capturar en Rust el `HWND` anterior justo antes de mostrar el overlay y enviarlo a React. Eso hara fiable el contexto de ventana.

Detalles: [docs/OVERLAY_WINDOWS.md](docs/OVERLAY_WINDOWS.md).

## Estructura

```text
src/
  agent.py                 Orquestador principal
  api/                     FastAPI, rutas, WebSockets y servicios
  rag/                     Ingestion, chunking y retrieval local
  tooling/                 Registry, permisos, auditoria y ejecucion de tools
  tools_catalog/           Tools locales y Windows
  os_integration/          Runtime Windows base
  orchestration/           Workflows agenticos iniciales
ui/desktop/
  src/                     React
  src-tauri/               Tauri/Rust, sidecar y overlay
docs/                      Documentacion tecnica
data/                      Datos locales ignorados por Git
```

## Roadmap De Implementacion

Estado verificado el **14 de junio de 2026**:

| Area | Estado | Madurez |
| --- | --- | ---: |
| Core agente local | EN VALIDACION | 75% |
| Seguridad, permisos y auditoria | EN VALIDACION | 70% |
| Windows Runtime | EN DESARROLLO | 60% |
| API local-first | EN VALIDACION | 85% |
| Desktop App | EN VALIDACION | 75% |
| Overlay Windows | EN VALIDACION | 55% |
| Computer Use | EN DESARROLLO | 45% |
| Workflows y automatizacion | EN DESARROLLO | 45% |
| OCR y contexto visual | EN DESARROLLO | 45% |
| RAG y memoria | EN VALIDACION | 70% |
| Build y distribucion | EN VALIDACION | 65% |
| Multi-modelo | NO INICIADO | 5% |
| Voz local | NO INICIADO | 0% |
| Personalizacion | NO INICIADO | 0% |

Prioridad actual: completar un flujo Computer Use real con UI Automation:
observar, localizar, confirmar, actuar y verificar.

El desglose, criterios de salida, hitos, riesgos y tareas priorizadas viven en
[docs/ROADMAP.md](docs/ROADMAP.md).

## Build Windows

```powershell
.\scripts\build-windows-app.ps1
```

Salidas esperadas:

```text
ui\desktop\src-tauri\target\release\bundle\nsis\IA Local Agent Setup.exe
ui\desktop\src-tauri\target\release\bundle\msi\IA Local Agent.msi
```

Mas detalles:

- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/COMPUTER_USE_MVP.md](docs/COMPUTER_USE_MVP.md)
- [docs/COMPUTER_USE_UAT.md](docs/COMPUTER_USE_UAT.md)
- [docs/DESKTOP_APP_MVP.md](docs/DESKTOP_APP_MVP.md)
- [docs/WINDOWS_APP_BUILD.md](docs/WINDOWS_APP_BUILD.md)
- [docs/api.md](docs/api.md)
- [docs/WINDOWS_OS_AGENT_ARCHITECTURE.md](docs/WINDOWS_OS_AGENT_ARCHITECTURE.md)
