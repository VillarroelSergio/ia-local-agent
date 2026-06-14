# Roadmap De IA Local Agent

Estado verificado el 14 de junio de 2026.

## Criterio De Estado

- `COMPLETADO`: alcance definido implementado y validado.
- `EN VALIDACION`: implementado como base, pero pendiente de UAT o pruebas reales.
- `EN DESARROLLO`: existe una parte funcional, faltan capacidades esenciales.
- `NO INICIADO`: no existe una implementacion util en el producto.

Los porcentajes son una estimacion de madurez, no una medida automatica de
lineas de codigo.

## Resumen Ejecutivo

IA Local Agent ya dispone de una plataforma local-first amplia: backend,
desktop, conversaciones, memoria/RAG, tools, seguridad base, runtime Windows,
overlay y Computer Use MVP. Sin embargo, todavia no funciona de extremo a
extremo como un copiloto Windows fiable.

El principal cuello de botella ya no es crear mas infraestructura. Es cerrar y
validar el bucle:

```text
intencion natural -> observar -> localizar control -> confirmar -> actuar -> verificar
```

La siguiente fase debe centrarse en Computer Use real sobre aplicaciones
Windows permitidas. Voz, multi-modelo y personalizacion quedan fuera del foco
inmediato.

## Estado Por Area

| Area | Estado | Madurez | Evidencia actual | Para cerrar la fase |
| --- | --- | ---: | --- | --- |
| Core agente local | EN VALIDACION | 75% | Orquestador, prompts, contexto, conversaciones, memoria, RAG y tools | Recuperacion de turnos, routing menos rigido y validacion prolongada con LM Studio |
| Seguridad, permisos y auditoria | EN VALIDACION | 70% | Risk levels, confirmaciones, allow/deny, politica OS, auditoria y sanitizacion de eventos | Token por instalacion, politica por app, UI de modo seguro y UAT sobre superficies sensibles |
| Windows Runtime | EN DESARROLLO | 60% | Ventanas, capturas, OCR base, eventos, hotkeys, workflows y scheduler | WinEvent nativo, UIA de actuacion, publishers del sistema y pruebas DPI/multi-monitor |
| API local-first | EN VALIDACION | 85% | FastAPI, auth local, chat, streaming, WebSockets, tools, workflows, cancelacion y Computer Use | Unificar cancelacion/errores y validar contratos contra desktop real |
| Desktop App | EN VALIDACION | 75% | Tauri + React, chat, historial, tools, timeline, settings, memoria y panel Computer Use | Pulido UX, adjuntos, estados de error, gestor RAG y pruebas empaquetadas |
| Overlay Windows | EN VALIDACION | 55% | Shortcut, ventana flotante, contexto activo, selector de ventana y OCR bajo demanda | Shortcut configurable real, persistencia Tauri, DPI/multi-monitor y confirmaciones robustas |
| Computer Use | EN DESARROLLO | 45% | Sesiones SQLite, Observe-Plan-Act-Verify, API, eventos, panel, UIA de lectura y routing natural | `invoke_control`, `set_text`, verificacion real, planner por app y nuevo UAT completo |
| Workflows y automatizacion | EN DESARROLLO | 45% | Runner, reintentos basicos, cancelacion, historial y scheduler | DSL estable, estado durable, condiciones visuales, rollback y monitor de tareas |
| OCR y contexto visual | EN DESARROLLO | 45% | Captura y Tesseract bajo demanda con politica de ventanas | Crop fiable, idiomas empaquetados, fallback controlado, DPI y proveedor local mejorado |
| RAG y memoria | EN VALIDACION | 70% | Chroma, ingestion segura, manifest, busqueda, memoria y panel basico | Borrado/reindexado por documento, fuentes visibles y pruebas con corpus real |
| Build y distribucion Windows | EN VALIDACION | 65% | Sidecar Python, scripts, configuracion Tauri y salidas NSIS/MSI | Smoke test de instalador limpio, dependencias OCR/UIA y token generado |
| Optimizacion | EN DESARROLLO | 25% | Algunas bases de eventos, cache y limites | Medicion de latencia, tokens, CPU/RAM, OCR y tiempos por fase |
| Multi-modelo / servidor IA | NO INICIADO | 5% | Abstraccion de providers y embeddings | Routing por tarea, Ollama/vLLM y configuracion de red local opcional |
| Voz local | NO INICIADO | 0% | Sin flujo de producto | Whisper.cpp, Piper, wake word, permisos y UX |
| Personalizacion avanzada | NO INICIADO | 0% | Sin flujo de producto | Perfiles, datasets, evaluacion, LoRA y especializacion |

## Hitos

### Hito 1 - Computer Use Util

Objetivo: completar una tarea sencilla en Notepad o una aplicacion Win32
permitida usando lenguaje natural.

Criterios de salida:

- Observar la ventana activa mediante UIA sin OCR por defecto.
- Encontrar un control por nombre, tipo o automation id.
- Pedir confirmacion antes de pulsar o escribir.
- Ejecutar `invoke_control` y `set_text` con bloqueo de campos sensibles.
- Verificar el resultado y mostrar evidencia segura.
- Superar los casos de `docs/COMPUTER_USE_UAT.md`.

### Hito 2 - Overlay Fiable

Objetivo: usar el agente desde cualquier aplicacion sin perder el contexto ni
romper la experiencia multi-monitor.

Criterios de salida:

- Shortcut configurable aplicado por Tauri.
- Contexto correcto de la ventana previa.
- Posicion y tamano persistidos fuera de `localStorage`.
- Confirmaciones visibles y no ambiguas.
- Validacion con VS Code, Explorer, navegador y Notepad en DPI alto.

### Hito 3 - Desktop MVP Candidato A Release

Objetivo: instalar y usar la aplicacion en un Windows limpio.

Criterios de salida:

- Instalador probado de principio a fin.
- Backend sidecar, OCR y UIA empaquetados.
- Token local generado por instalacion.
- Errores de LM Studio accionables.
- Chat, historial, RAG, tools, overlay y Computer Use pasan smoke test.

### Hito 4 - Workflows Reutilizables

Objetivo: guardar, reanudar y supervisar automatizaciones seguras.

Criterios de salida:

- DSL estable y persistencia SQLite.
- Condiciones UIA/visuales, reintentos y cancelacion.
- Rollback basico cuando la accion lo permita.
- Monitor de tareas y auditoria legible.

### Hito 5 - Capacidades Futuras

Solo se inicia tras validar los hitos anteriores:

- Voz local.
- Routing multi-modelo.
- Optimizacion avanzada.
- Personalizacion y LoRA.

## Proximas Tareas Priorizadas

1. Implementar `UIAutomationService.invoke_control`.
2. Implementar `UIAutomationService.set_text` y bloquear password fields.
3. Conectar ambas operaciones al executor de Computer Use.
4. Verificar acciones mediante una nueva observacion UIA.
5. Repetir y actualizar `COMPUTER_USE_UAT.md` con resultados reales.
6. Probar overlay y Computer Use con Notepad, Explorer y VS Code.
7. Empaquetar y probar dependencias UIA/OCR en el instalador.
8. Cerrar shortcut y bounds persistentes del overlay.
9. Anadir borrado/reindexado y fuentes al panel RAG.
10. Medir latencia del flujo completo antes de optimizar.

## Riesgos Principales

- Los tests con mocks pueden pasar aunque UI Automation falle en Windows real.
- Electron, canvas y aplicaciones minimizadas pueden no exponer controles UIA.
- DPI, foco y multi-monitor pueden dirigir una accion a una ventana incorrecta.
- OCR y dependencias UIA pueden romper el empaquetado.
- El roadmap puede aparentar mas madurez por cantidad de infraestructura que
  por tareas de usuario completadas.

## Fuentes De Evidencia

- `README.md`
- `docs/COMPUTER_USE_MVP.md`
- `docs/COMPUTER_USE_UAT.md`
- `docs/COMPUTER_USE_RUNTIME.md`
- `docs/WINDOWS_OS_AGENT_ARCHITECTURE.md`
- `docs/DESKTOP_APP_MVP.md`
- `docs/OVERLAY_WINDOWS.md`
- `docs/RAG_ARCHITECTURE.md`
- `docs/WINDOWS_APP_BUILD.md`
- `tests/api/`, `tests/e2e/`, `tests/computer_use/`
- `ui/desktop/src/features/computer-use/`
