# Desktop UAT - Computer Use Actions

## Entorno

- Rama: `feature/computer-use-mvp`
- Base: `3c459f8`
- Fecha: 14 de junio de 2026
- Backend y LM Studio: disponibles
- Modelo: `qwen/qwen3.5-9b`
- Aplicacion objetivo: Notepad
- Documento temporal: identificador `computer-use-uat-20260614-unique`

## Decision Del Gate

`BLOCKED`

La implementacion tecnica y las pruebas automatizadas pasan, pero no se cumple
el criterio de salida real. Notepad abrio el documento temporal dentro de un
PID preexistente. Conforme al protocolo Desktop UAT, se aborto antes de
escribir, pulsar Guardar o cerrar la ventana.

No se actualiza `docs/ROADMAP.md`.

## Resultados

| Caso | Resultado | Evidencia |
| --- | --- | --- |
| Analizar ventana sin OCR | PASS tecnico | Routing a `observe_window`; UIA read-only |
| Escribir texto | BLOCKED real | No se actuo sobre un PID preexistente |
| Buscar Guardar sin pulsar | PASS tecnico | Busqueda read-only; no abre menu ni actua |
| Pulsar Guardar | BLOCKED real | Implementado menu bajo demanda tras confirmacion; no ejecutado por falta de aislamiento |
| Verificar texto | PASS automatizado | `ValuePattern.Value` se reconsulta; escritura no verificada devuelve fallo |
| Rechazar confirmacion | PASS automatizado | El adaptador no se invoca sin grant |
| Campo sensible | PASS automatizado | Controles password/secret/token se bloquean antes del adaptador |
| Cambio de foco | PASS automatizado | La identidad foreground se comprueba y cancela la accion |
| UI Tauri visible | BLOCKED | No hay acceso visual conectado a la interfaz |

## Evidencia Real Read-Only

- Se creo un proceso nuevo al intentar `/new-window`, pero Notepad rechazo el
  argumento como nombre de archivo. Ese proceso UAT se cerro de forma aislada.
- Al abrir solo la ruta, Notepad reutilizo el PID preexistente.
- La inspeccion UIA encontro un `DocumentControl` con nombre `Text editor`.
- `Save/Guardar` no aparece en el arbol hasta desplegar `File/Archivo`.
- No se escribio ni se guardo contenido durante esta ejecucion.

## Validacion Automatizada

- Python completo: `141 passed`.
- Computer Use + API + e2e focalizado tras el ultimo ajuste: `82 passed`.
- Frontend: `6 passed`.
- Frontend build: `PASS`.
- Cargo check: `PASS`.

## Implementacion Validada

- Referencias UIA con HWND, PID, titulo y path del control.
- Re-resolucion del nodo justo antes de actuar.
- Cancelacion si cambia foco, PID, HWND, titulo o selector.
- `Invoke`, `Select`, `Toggle` y click semantico como fallback.
- `ValuePattern.SetValue` y `SendKeys` controlado como fallback.
- Verificacion posterior de escritura.
- Alias de controles en espanol e ingles.
- Menu `File/Archivo` bajo demanda solo dentro de una accion confirmada.
- Tools `click_ui_control` y `fill_text_field`.
- Routing natural para `Escribe ... en el documento` y `Pulsa Guardar`.
- Argumentos de texto pendientes guardados solo en memoria y redactados en
  sesion/eventos.

## Riesgos Residuales

- Notepad moderno puede reutilizar proceso y ventana, impidiendo un UAT aislado.
- Confirmar desde Tauri cambia el foco; la accion se cancela de forma segura,
  pero falta un mecanismo para fijar/restaurar la ventana objetivo desde UI.
- No se ha observado visualmente el modal ni el timeline Tauri.
- El guardado real mediante menu bajo demanda no tiene evidencia en una
  instancia aislada.

## Siguiente Paso

Crear un harness de aplicacion Win32 de prueba controlada o un mecanismo de
target pinning en Tauri que conserve HWND/PID antes de mostrar confirmacion.
Despues repetir el flujo completo y solo entonces actualizar el roadmap.

