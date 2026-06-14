# IA Local Agent - Agent Guide

Guia operativa para agentes que desarrollen este proyecto.

## Repositorio

Trabaja siempre sobre este repositorio local, que corresponde al proyecto alojado en:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

Antes de proponer cambios grandes, asume que el codigo fuente, scripts, docs y tests relevantes estan dentro de este workspace. No crees soluciones fuera del repo salvo que el usuario lo pida explicitamente.

## Producto

IA Local Agent es un copiloto local para Windows. Usa LM Studio como proveedor LLM, FastAPI como backend local-first y una app Tauri + React como interfaz desktop. El objetivo es evolucionar desde chat local hacia un copiloto privado con memoria, RAG, tools, overlay contextual, automatizacion segura y voz local.

## Estado Del Proyecto

El proyecto esta en cierre de Desktop App MVP e inicio/refinamiento del Overlay Windows.

Funcional como base:

- API FastAPI local en `127.0.0.1:8765`.
- Chat, streaming, WebSocket y conversaciones persistentes.
- Memoria semantica y RAG local sobre ChromaDB.
- Tool calling con registry, permisos, confirmaciones y auditoria JSONL.
- Desktop app Tauri + React con chat, historial, tools, timeline, settings y memoria.
- Runtime Windows base: ventanas, capturas, OCR base, eventos, hotkeys, workflows y scheduler.
- Overlay Tauri inicial con `Ctrl+Alt+Space`, ventana compacta y contexto seguro de ventana activa.

Problemas conocidos:

- El overlay necesita pruebas reales con apps Windows, DPI alto y multi-monitor.
- `Sin contenido` en chat suele apuntar a LM Studio, base URL o modelo mal configurado.
- UI Automation selectors no esta implementado.
- OCR y workflows existen como base, pero no estan cerrados como experiencia de usuario.

## Estructura

```text
src/
  agent.py                 Orquestador principal
  api/                     FastAPI, rutas, WebSockets, schemas y servicios
  rag/                     Ingestion, chunking, seguridad, manifest y retrieval
  tooling/                 Registry, permisos, auditoria y ejecucion de tools
  tools_catalog/           Tools locales y Windows
  os_integration/          Runtime Windows base usado por tools actuales
  windows/                 Fachada de dominio Windows en evolucion
  orchestration/           Workflows agenticos iniciales
ui/desktop/
  src/                     React, servicios API/WS y features UI
  src-tauri/               Tauri v2, Rust, sidecar backend y overlay
docs/                      Documentacion tecnica
tests/                     Tests API y e2e Python
scripts/                   Arranque y build Windows
data/                      Datos locales ignorados por Git
.agents/                   Perfiles de agentes especializados
```

## Comandos Habituales

Backend:

```powershell
venv\Scripts\python.exe -m src.api.main
venv\Scripts\python.exe -m pytest tests\api\test_api.py
venv\Scripts\python.exe -m pytest tests\e2e
```

Frontend:

```powershell
cd ui\desktop
npm run test
npm run build
npm run tauri:dev
```

Rust/Tauri:

```powershell
cd ui\desktop\src-tauri
cargo check
```

Build Windows:

```powershell
.\scripts\build-windows-app.ps1
.\scripts\build-windows-app.ps1 -NoVersionBump
```

Comprobaciones manuales:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health
Invoke-RestMethod http://127.0.0.1:8765/api/status
Invoke-RestMethod http://127.0.0.1:1234/v1/models
```

## Variables Y Servicios

LM Studio debe exponer servidor OpenAI-compatible en:

```text
http://127.0.0.1:1234/v1
```

Variables importantes:

```env
DEFAULT_PROVIDER=lmstudio
DEFAULT_MODEL=qwen/qwen3.5-9b
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_API_KEY=lm-studio
LOCAL_API_KEY=local-dev-token
API_HOST=127.0.0.1
API_PORT=8765
LLM_NATIVE_TOOLS_ENABLED=false
```

Para tests o desarrollo sin embeddings remotos:

```env
SEMANTIC_EMBEDDING_PROVIDER=local_hash
```

## Principios De Desarrollo

- Mantener local-first: no introducir dependencias de red obligatorias para flujos centrales.
- Respetar la separacion: UI llama API; no duplicar logica del agente en React.
- Las tools sensibles pasan por `ToolExecutor`, permisos, politica OS, confirmacion y auditoria.
- El overlay no captura pantalla, no hace OCR continuo y no automatiza acciones sensibles sin una accion explicita del usuario.
- En modo desktop empaquetado, datos modificables viven en `AppData\Local\IA Local Agent`, nunca en `Program Files`.
- No empaquetar `.env`, `data`, SQLite, Chroma ni logs privados.
- Preferir capacidades semanticas (`focus_window`, `extract_visible_text`) frente a primitivas crudas (`click`, `type_text`).
- Mantener errores visibles y seguros: utiles para usuario, sin stack traces en UI.
- Antes de tocar Windows runtime, revisar seguridad, DPI, multi-monitor, UAC y ventanas sensibles.

## Documentos Clave

- `docs/reference/IA_LOCAL_WINDOWS.md`: vision, roadmap conceptual y recursos importados desde Notion.
- `docs/reference/IA_LOCAL_WINDOWS.pdf`: exportacion original con el diagrama de arquitectura/roadmap.
- `README.md`: estado, roadmap, arranque rapido y tareas recomendadas.
- `docs/api.md`: contrato API, auth, chat, WebSocket, seguridad.
- `docs/DESKTOP_APP_MVP.md`: arquitectura de desktop app y endpoints usados.
- `docs/OVERLAY_WINDOWS.md`: alcance, seguridad y contrato de overlay.
- `docs/WINDOWS_OS_AGENT_ARCHITECTURE.md`: runtime Windows, eventos, OCR, workflows.
- `docs/RAG_ARCHITECTURE.md`: ingestion, retrieval, seguridad y evolucion RAG.
- `docs/WINDOWS_APP_BUILD.md`: sidecar, instalador, lifecycle y checklist de build.

## Agentes Especializados

Usa estos perfiles para revisar, planificar o implementar cambios por area:

- `.agents/README.md`
- `.agents/ceo-agent.md`
- `.agents/planner-agent.md`
- `.agents/head-of-engineering-agent.md`
- `.agents/designer-agent.md`
- `.agents/builder-agent.md`
- `.agents/bug-agent.md`
- `.agents/testing-agent.md`
- `.agents/backend-api-agent.md`
- `.agents/frontend-tauri-agent.md`
- `.agents/windows-overlay-agent.md`
- `.agents/rag-memory-agent.md`
- `.agents/qa-test-agent.md`
- `.agents/user-acceptance-test-agent.md`
- `.agents/build-release-agent.md`
- `.agents/product-planning-agent.md`

Cada perfil incluye foco, archivos a leer, tareas tipicas, validaciones y limites. Para tareas grandes, combina agentes: por ejemplo overlay + frontend + QA, o RAG + backend + QA.

Los siete agentes transversales dirigen el trabajo; los agentes especializados
aportan conocimiento de dominio. No es obligatorio usar las siete capas en
tareas pequenas. En iniciativas ambiguas o transversales, la ruta por defecto
es `CEO -> Planificador -> Jefe de Ingenieria -> Diseñador/Constructor ->
Bugs/Testeo`, sumando los especialistas necesarios.

Plantillas y playbooks:

- `.agents/task-templates/feature.md`
- `.agents/task-templates/bugfix.md`
- `.agents/task-templates/security-review.md`
- `.agents/task-templates/release-check.md`
- `.agents/task-templates/overlay-change.md`
- `.agents/task-templates/rag-change.md`
- `.agents/task-templates/user-acceptance-test.md`
- `.agents/decision-trace-template.md`
- `docs/TESTING_MATRIX.md`
- `docs/playbooks/diagnose-lmstudio.md`
- `docs/playbooks/debug-overlay.md`
- `docs/playbooks/build-windows-release.md`
- `docs/playbooks/add-api-endpoint.md`
- `docs/playbooks/add-tool.md`
- `docs/playbooks/add-rag-feature.md`

## Checklist Antes De Cerrar Una Tarea

- El cambio respeta la arquitectura local-first.
- Hay manejo de errores visible y seguro.
- Las acciones sensibles tienen confirmacion o denegacion explicita.
- Se actualizaron tipos/schemas si cambio el contrato API.
- Se ejecutaron las pruebas razonables para el area tocada, o se documento por que no.
- Se actualizo documentacion cuando cambia arranque, contrato, seguridad o build.
- No se introdujeron secretos, rutas privadas absolutas innecesarias ni datos locales en Git.

## Trazabilidad De Decisiones

Cuando el usuario envie un prompt de desarrollo, pruebas, build o planificacion, muestra una traza breve antes de ejecutar cambios si la tarea tiene ambiguedad, riesgo o cruza varias areas.

Formato recomendado:

```text
Ruta de agentes:
- Principal: <agente> porque <razon>
- Apoyo: <agente> porque <razon>
- QA: <agente> porque <riesgo/pruebas>

Decisiones iniciales:
- <decision>: <motivo>
- <decision>: <motivo>

Validacion prevista:
- <comando o comprobacion>
```

Durante el trabajo, actualiza la traza si cambian los hechos: nuevo agente necesario, decision revertida, prueba fallida, riesgo descubierto o alcance reducido.

Al cerrar, resume:

- Agentes usados.
- Decisiones tomadas.
- Archivos cambiados.
- Pruebas ejecutadas o no ejecutadas.
- Riesgos residuales.

Usa `.agents/decision-trace-template.md` cuando convenga dejar una traza mas completa.
