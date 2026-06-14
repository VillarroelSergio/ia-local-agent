# IA Local Windows - Fuente De Producto

Documento de referencia para agentes que trabajan en IA Local Agent.

## Procedencia

- Fuente original: exportacion de la pagina Notion `IA LOCAL WINDOWS`.
- Importado al repositorio: 2026-06-14.
- PDF original: [`IA_LOCAL_WINDOWS.pdf`](IA_LOCAL_WINDOWS.pdf).
- Repositorio: `https://github.com/VillarroelSergio/ia-local-agent`.

El PDF conserva la presentacion y el diagrama originales. Este Markdown hace
su contenido localizable y legible por agentes. El estado vigente se mantiene
en [`../ROADMAP.md`](../ROADMAP.md).

## Regla De Uso

Esta fuente expresa vision de producto, recursos y roadmap conceptual. El
codigo, los tests, `README.md` y la documentacion tecnica de `docs/` son la
fuente de verdad para el estado implementado.

Cuando exista una discrepancia:

1. Verificar el comportamiento en codigo y tests.
2. Consultar la documentacion tecnica del area.
3. Tratar el estado del PDF como una fotografia historica.
4. Proponer una actualizacion documental en vez de asumir que el PDF esta al dia.

No introducir una dependencia, framework o servicio solo porque aparezca en
la lista de recursos. Debe justificar una necesidad real y respetar
local-first.

## Vision

Construir un agente local para Windows que evolucione desde chat hacia un
copiloto privado con:

- Core de agente modular.
- Seguridad, permisos y auditoria.
- Runtime operativo de Windows.
- API local-first.
- Aplicacion desktop.
- Overlay contextual.
- Automatizacion avanzada.
- Voz local.
- Optimizacion de latencia, retrieval, OCR, tokens y eventos.
- Routing multi-modelo y servidor IA local.
- Personalizacion mediante datasets, LoRA y especializacion.

## Roadmap Conceptual Del Documento

| Area | Elementos recogidos en la fuente |
| --- | --- |
| Core agente local | Backend modular, providers, prompts, contexto, conversaciones, memoria, tool calling y RAG |
| Seguridad | Niveles de riesgo, confirmaciones, allowlist/denylist, auditoria y bloqueo de superficies sensibles |
| Windows Runtime | WindowManager, capturas, OCR, UI Automation, eventos, hotkeys, workflows y scheduler |
| API local-first | FastAPI, chat, streaming, WebSockets, tools, workflows, confirmaciones y cancelacion |
| Desktop App MVP | Chat, historial, panel de tools, timeline, configuracion y memoria/RAG |
| Overlay Windows | Shortcut global, ventana flotante, contexto de ventana activa y confirmaciones seguras |
| Automatizacion avanzada | Workflows reutilizables, selectores UI, planner visual, reintentos y rollback basico |
| Voz local | Whisper.cpp, Piper TTS y wake word |
| Optimizacion | Latencia, retrieval, OCR, tokens y eventos |
| Multi-modelo | Routing por tarea, embeddings separados, Ollama/vLLM y API de red local |
| Personalizacion | Datasets, LoRA y especializacion |

Para el estado vigente, consultar el roadmap de `README.md` y los documentos
tecnicos del area.

## Recursos Recogidos

- Hugging Face Transformers: `https://huggingface.co/docs/transformers/`
- LangChain: `https://docs.langchain.com/oss/python/langchain/overview`
- LangGraph: `https://docs.langchain.com/oss/python/langgraph/overview`
- OpenAI function calling: `https://developers.openai.com/api/docs/guides/function-calling`
- LM Studio: `https://lmstudio.ai/docs/app`
- llama.cpp: `https://github.com/ggml-org/llama.cpp`
- Chroma: `https://docs.trychroma.com/docs/overview/introduction`

Los enlaces son material de investigacion, no dependencias aprobadas.

## Documentacion Relacionada

- `README.md`: estado y roadmap vigente.
- `docs/ROADMAP.md`: estado verificado, hitos y prioridades vigentes.
- `docs/WINDOWS_OS_AGENT_ARCHITECTURE.md`: runtime Windows.
- `docs/COMPUTER_USE_RUNTIME.md`: Computer Use.
- `docs/DESKTOP_APP_MVP.md`: aplicacion desktop.
- `docs/OVERLAY_WINDOWS.md`: overlay.
- `docs/RAG_ARCHITECTURE.md`: RAG y memoria.
- `docs/api.md`: contrato API.
- `.agents/README.md`: estructura de agentes.
