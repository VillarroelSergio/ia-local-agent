# Computer Use MVP

## Arquitectura

Computer Use amplia el runtime Windows existente sin sustituir `LocalAgent`,
`ToolExecutor`, `WorkflowRunner`, `EventBus` ni `OSSecurityPolicy`.

```text
API/UI -> ComputerUseEngine -> Observe -> Plan -> Policy/Confirm -> Act -> Verify
```

Las tools publicas continuan pasando por `ToolExecutor`. Las confirmaciones
internas son temporales, ligadas a sesion y capability, y de un solo uso.

## Endpoints

```text
GET  /api/computer-use/status
POST /api/computer-use/sessions
GET  /api/computer-use/sessions
GET  /api/computer-use/sessions/{id}
POST /api/computer-use/sessions/{id}/run
POST /api/computer-use/sessions/{id}/cancel
POST /api/computer-use/sessions/{id}/confirm
POST /api/computer-use/observe
POST /api/computer-use/observe/window
POST /api/computer-use/find-control
POST /api/computer-use/execute-capability
```

`POST /api/computer-use/run` se conserva como wrapper compatible.

## Seguridad Y Eventos

`WS /ws/events` recibe eventos sanitizados con `session_id`,
`correlation_id`, `timestamp`, `status`, `safe_summary`, `current_step` y
`risk_level`. No se emiten screenshots, OCR crudo, passwords, tokens ni rutas.

OCR solo se activa bajo peticion explicita. UIA y OCR se bloquean antes de leer
una ventana sensible. Las capabilities de control requieren confirmacion.

## Capabilities

Lectura: `observe_desktop`, `observe_active_window`, `extract_visible_text`,
`summarize_active_window`, `find_ui_control`.

Alto riesgo: `focus_window`, `click_ui_control`, `fill_text_field`,
`organize_windows`, `run_safe_workflow`.

Las capabilities sin adaptador estable fallan de forma controlada despues de
la confirmacion; nunca simulan una ejecucion correcta.

## Ejemplo

```powershell
$headers = @{ "x-api-key" = "local-dev-token" }
$session = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8765/api/computer-use/sessions `
  -Headers $headers -ContentType application/json `
  -Body '{"goal":"Analiza la ventana activa"}'
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8765/api/computer-use/sessions/$($session.id)/run" `
  -Headers $headers
```

## Acciones UIA

Tools confirmadas disponibles:

- `click_ui_control`
- `fill_text_field`

Ambas validan HWND, PID, titulo, foco e identidad del control inmediatamente
antes de actuar. La escritura se verifica releyendo `ValuePattern`. Los textos
pendientes de confirmacion no se persisten en SQLite ni eventos.

## Limitaciones

- UIA depende del soporte de accesibilidad de cada aplicacion.
- Electron, canvas, juegos y ventanas minimizadas pueden no exponer controles.
- Click y escritura UIA estan implementados, pero pendientes de UAT aislado.
- Confirmar desde Tauri puede cambiar el foco; la accion se cancela si la
  ventana objetivo no permanece activa.
- VisionProvider sigue siendo futuro.
- DPI y multi-monitor requieren validacion manual.
