# Computer Use MVP Review

## Ruta De Agentes

- Planificacion: `product-planning-agent.md`.
- Runtime Windows: `windows-overlay-agent.md`.
- API: `backend-api-agent.md`.
- UI: `frontend-tauri-agent.md`.
- Validacion: `qa-test-agent.md` y `user-acceptance-test-agent.md`.

## Estado Existente

- `ComputerUseEngine` implementa un ciclo Observe/Plan/Act/Verify.
- `DesktopObserver` prioriza WindowManager, UI Automation y OCR explicito.
- `ComputerUseExecutor` delega acciones en `WorkflowRunner`.
- Las tools Computer Use ya pasan por el registry y `ToolExecutor`.
- Hay persistencia SQLite basica, rutas FastAPI y un panel React inicial.

## Incompleto

- `/run` bloquea hasta el final y no permite seguir una sesion desde su creacion.
- Los eventos del runtime Windows y `/ws/events` usan buses distintos.
- La cancelacion no conserva una asociacion fiable entre sesion y workflow.
- El riesgo se calcula, pero una sesion no se pausa y reanuda de forma persistente.
- Las sesiones no guardan plan, verificaciones, errores ni decisiones de politica por separado.
- UI Automation de invocacion y escritura sigue siendo opcional e incompleta.
- El verifier acepta objetivos no vacios sin comprobar un resultado observable.
- El panel genera parte de su timeline localmente en vez de consumir progreso real.

## Riesgos

- Crear una via de confirmacion paralela que pueda saltarse `ToolExecutor`.
- Ejecutar sobre una ventana distinta entre aprobacion y accion.
- Persistir o emitir OCR, screenshots, rutas o texto sensible.
- Bloquear el event loop con UI Automation.
- Romper sesiones SQLite existentes durante la migracion.

## Plan

1. Ampliar contratos y persistencia de forma compatible.
2. Separar crear y ejecutar sesion, con cancelacion cooperativa.
3. Puentear eventos sanitizados hacia `/ws/events`.
4. Pausar capabilities de alto riesgo y reutilizar el flujo de confirmacion.
5. Completar observacion, verificacion y reintentos controlados.
6. Conectar el panel Tauri con el contrato real.
7. Ejecutar pruebas automatizadas y preparar UAT por prompts.
