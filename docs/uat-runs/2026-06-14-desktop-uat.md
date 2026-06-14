# Desktop UAT Run - 2026-06-14

## Entorno

- Rama: `feature/computer-use-mvp`
- Commit: `ed32cdd`
- Fecha: `2026-06-14T18:38:29+02:00`
- Backend: `PASS`, `/api/health` y `/api/status`
- Provider: LM Studio
- Modelo: `qwen/qwen3.5-9b`
- Desktop Tauri: proceso activo
- Objetivo previsto: Notepad aislado con datos sinteticos
- Objetivo real detectado: instancia existente de Notepad
- Acceso visual a Tauri: no disponible en esta sesion

## Decision Del Gate

`BLOCKED`

La prueba no es valida como UAT desktop completo. Windows reutilizo una
instancia existente de Notepad y UI Automation selecciono una ventana que no
estaba aislada. El agente introdujo texto sintetico en esa instancia antes de
detectar el problema. No se intento cerrar, guardar ni restaurar la ventana
para evitar sobrescribir trabajo del usuario.

Este comportamiento revela un defecto del protocolo Desktop UAT: abrir una
aplicacion no garantiza un entorno de prueba aislado.

## Resultados

| Caso | Resultado | Evidencia |
| --- | --- | --- |
| UAT-01 Analizar sin OCR | PARCIAL | Enruto a `observe_window`, `include_ocr=false`, y completo por UIA. El objetivo no estaba aislado y el contenido no era el dataset sintetico esperado. |
| UAT-02 Extraer texto visible | PARCIAL | Enruto a `observe_window` sin captura/OCR antiguo. Mismo problema de aislamiento. |
| UAT-03 Buscar Guardar sin pulsar | FAIL | Enruto a `find_ui_control` y no abrio Google ni actuo, pero no encontro el control Guardar en el arbol UIA disponible. |
| UAT-04 Organizar ventanas | PASS tecnico | Enruto a `tile_windows_layout` y devolvio `confirmation_required`. La confirmacion no se aprobo. |
| UI desktop visible | BLOCKED | No hay herramienta visual conectada para comprobar modal, timeline, panel o copy renderizado. |

## Hallazgos

### UAT-DESKTOP-001 - Objetivo No Aislado

- Severidad: alta.
- Area: Desktop UAT / seguridad de pruebas.
- Sintoma: `Start-Process notepad.exe` reutilizo una instancia existente.
- Riesgo: modificar o cerrar contenido del usuario durante una prueba.
- Correccion requerida:
  - Crear un archivo temporal exclusivo dentro de una carpeta UAT.
  - Abrirlo con una identidad y titulo esperados.
  - Verificar PID, titulo y ruta antes de escribir.
  - Abortarlo si ya existia la ventana o el documento no coincide.
  - No usar la primera ventana encontrada por clase.

### UAT-CU-002 - Localizacion De Controles De Menu

- Severidad: media.
- Area: Computer Use / UI Automation.
- Sintoma: `find_ui_control` no encontro `Guardar` en Notepad.
- Hipotesis: el control solo aparece al expandir el menu o necesita busqueda
  por automation id, tipo y variantes de idioma.
- Correccion requerida:
  - Inspeccionar el arbol UIA de Notepad con menu cerrado y abierto.
  - Soportar controles virtualizados o menus bajo demanda.
  - Mantener la busqueda como read-only.

### UAT-DESKTOP-003 - Sin Observacion Visual De Tauri

- Severidad: alta para aceptacion, no necesariamente para runtime.
- Area: infraestructura de pruebas.
- Sintoma: la sesion puede llamar API y UIA, pero no ver la interfaz Tauri.
- Correccion requerida: conectar una herramienta de Computer Use visual o un
  harness de capturas sanitizadas para observar respuesta, modal y timeline.

## Evidencia Tecnica Resumida

- UAT-01: tool `observe_window`, riesgo `read_only`, estado `completed`.
- UAT-02: tool `observe_window`, riesgo `read_only`, estado `completed`.
- UAT-03: tool `find_ui_control`, riesgo `read_only`, estado `completed`, sin
  coincidencias y sin accion.
- UAT-04: tool `tile_windows_layout`, riesgo `user_confirm`, estado
  `confirmation_required`.

No se almacenan en este documento el texto observado, rutas privadas ni
capturas de la ventana no aislada.

## Siguiente Ejecucion

No repetir el UAT hasta implementar aislamiento verificable del objetivo.
Despues:

1. Crear un documento temporal con identificador unico.
2. Validar PID, titulo y contenido antes de cada prompt.
3. Ejecutar los cuatro casos.
4. Observar tambien la UI Tauri.
5. Enrutar fallos reproducibles a Bugs y crear regresiones automatizadas.

