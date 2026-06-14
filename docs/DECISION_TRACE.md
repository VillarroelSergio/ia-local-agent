# Decision Trace

Este documento define como mostrar trazabilidad de enrutamiento de agentes y decisiones durante el desarrollo de IA Local Agent.

## Objetivo

Que cada prompt relevante deje claro:

- Que agentes se usan.
- Por que se usan.
- Que decisiones se toman.
- Que alternativas se descartan.
- Que pruebas validan el resultado.
- Que riesgos quedan abiertos.

## Cuando Mostrar Traza

Mostrar traza siempre que la tarea:

- Toque varias areas, por ejemplo backend + frontend.
- Afecte seguridad, tools, overlay, OCR, RAG, build o release.
- Cambie contratos API o tipos compartidos.
- Requiera elegir entre enfoques.
- Tenga ambiguedad de alcance.
- Pueda generar regresiones importantes.

Para cambios triviales de un archivo o preguntas simples, basta con una traza corta o ninguna si entorpece.

## Formato Corto

```text
Ruta de agentes:
- Principal: backend-api-agent.md porque cambia endpoints/chat/tools.
- Apoyo: frontend-tauri-agent.md porque la UI consume el contrato.
- QA: qa-test-agent.md porque hay que validar API y build frontend.

Decisiones:
- Mantener logica en servicios, no en rutas.
- Actualizar tipos frontend junto al schema.

Validacion:
- pytest tests/api/test_api.py
- npm run build
```

## Formato Completo

Usar `.agents/decision-trace-template.md` cuando:

- La tarea es larga.
- Hay decisiones de arquitectura.
- Hay riesgo de seguridad.
- Se prepara release.
- El usuario pide trazabilidad completa.

## Enrutamiento Base

| Prompt menciona... | Agente principal | Apoyo |
| --- | --- | --- |
| API, chat, provider, settings, tools | `backend-api-agent.md` | `qa-test-agent.md` |
| UI, React, Vite, paneles, settings modal | `frontend-tauri-agent.md` | `qa-test-agent.md` |
| Overlay, HWND, OCR, hotkey, Windows runtime | `windows-overlay-agent.md` | `frontend-tauri-agent.md`, `qa-test-agent.md` |
| RAG, memoria, Chroma, fuentes, ingestion | `rag-memory-agent.md` | `backend-api-agent.md`, `qa-test-agent.md` |
| Tests, bug, regression, review | `qa-test-agent.md` | Agente del area |
| Pruebas por prompt para usuario, UAT, resultados de prueba | `user-acceptance-test-agent.md` | `qa-test-agent.md`, agente del area |
| Build, release, instalador, sidecar | `build-release-agent.md` | `qa-test-agent.md` |
| Roadmap, priorizacion, desglose | `product-planning-agent.md` | Agente tecnico del area |

## Decisiones Que Deben Quedar Registradas

- Donde vive la logica: ruta, servicio, core, UI, Tauri o runtime Windows.
- Si una accion requiere confirmacion humana.
- Si se actualiza o no el contrato API.
- Si se anade test automatizado o solo comprobacion manual.
- Si se toca documentacion.
- Si se evita una opcion por seguridad, complejidad o riesgo de build.

## Cierre

La respuesta final debe incluir, en breve:

- Agentes usados.
- Decisiones clave.
- Archivos modificados.
- Pruebas ejecutadas.
- Riesgos residuales.
