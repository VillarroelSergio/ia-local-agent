# Agents Index

Indice de agentes para desarrollar IA Local Agent.

## Repositorio

Todos los agentes trabajan sobre este repositorio local, correspondiente a:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

Usa siempre archivos, scripts y tests del workspace actual como fuente de verdad. Si una tarea requiere cambios fuera del repo, pide confirmacion antes.

## Que Agente Usar

| Necesito... | Agente principal | Agentes de apoyo |
| --- | --- | --- |
| Cambiar chat, API, settings, tools o providers | `backend-api-agent.md` | `qa-test-agent.md` |
| Tocar React, servicios frontend, settings UI o paneles | `frontend-tauri-agent.md` | `backend-api-agent.md`, `qa-test-agent.md` |
| Mejorar overlay, OCR, ventanas, hotkeys o workflows Windows | `windows-overlay-agent.md` | `frontend-tauri-agent.md`, `qa-test-agent.md` |
| Cambiar ingestion, memoria, Chroma, fuentes o panel RAG | `rag-memory-agent.md` | `backend-api-agent.md`, `qa-test-agent.md` |
| Preparar instalador, sidecar, versionado o release Windows | `build-release-agent.md` | `qa-test-agent.md` |
| Definir roadmap, dividir tareas o priorizar mejoras | `product-planning-agent.md` | El agente tecnico del area |
| Revisar riesgos, pruebas y regresiones | `qa-test-agent.md` | Todos los anteriores |
| Preparar pruebas por prompt para que el usuario valide cambios | `user-acceptance-test-agent.md` | `qa-test-agent.md`, agente del area |
| Analizar resultados de pruebas del usuario y enrutar fixes | `user-acceptance-test-agent.md` | Agente corrector correspondiente |

## Combinaciones Recomendadas

| Tipo de tarea | Secuencia recomendada |
| --- | --- |
| Nueva feature API + UI | `product-planning` -> `backend-api` -> `frontend-tauri` -> `qa-test` |
| Fix de bug | `qa-test` -> agente del area -> `qa-test` |
| Cambio de seguridad | `qa-test` -> agente del area -> `backend-api` -> `qa-test` |
| Mejora de overlay | `windows-overlay` -> `frontend-tauri` -> `qa-test` |
| Release | `build-release` -> `qa-test` -> `build-release` |
| Validacion conversacional de usuario | `user-acceptance-test` -> usuario escribe prompts -> agente corrector -> `qa-test` |

## Plantillas

Usa `.agents/task-templates/` para arrancar tareas de forma consistente:

- `feature.md`: funcionalidades nuevas.
- `bugfix.md`: errores y regresiones.
- `security-review.md`: permisos, secretos, automatizacion y datos sensibles.
- `release-check.md`: build, versionado e instalador.
- `overlay-change.md`: ventana flotante, OCR, hotkeys y contexto Windows.
- `rag-change.md`: ingestion, retrieval, memoria y fuentes.
- `user-acceptance-test.md`: pruebas por prompt para usuario y reporte de resultados.

## Reglas Cortas

- Lee `AGENT.md` antes de actuar.
- Lee el agente principal y al menos un agente de apoyo para tareas de riesgo.
- Consulta `docs/TESTING_MATRIX.md` antes de cerrar cambios.
- Muestra una traza de enrutamiento y decisiones cuando la tarea tenga ambiguedad, riesgo o toque varias areas.
- Actualiza docs si cambia arranque, contrato API, seguridad, build o flujo de usuario.
- No introduzcas dependencias de red obligatorias para flujos centrales.
- No expongas secretos, rutas privadas innecesarias ni datos locales.

## Trazabilidad

Usa `.agents/decision-trace-template.md` para registrar:

- Prompt recibido.
- Agente principal y agentes de apoyo.
- Motivo de cada agente.
- Decisiones iniciales.
- Alternativas descartadas.
- Cambios de rumbo durante la tarea.
- Validaciones ejecutadas.
- Riesgos residuales.

Para tareas pequenas, basta con mostrar la traza en la respuesta. Para tareas largas o sensibles, crea o actualiza una nota de traza en el PR, issue o documento que indique el usuario.
