# Diagnostico Computer Use UAT

Fecha: 14 de junio de 2026.

## Conclusion

El UAT manual demuestra que Computer Use no funciona todavia como capacidad
de producto. Existen adaptadores, tools, API y pruebas aisladas, pero el chat
no los orquesta como una tarea Windows de extremo a extremo.

## Fallos Confirmados

- Un prompt compuesto que empieza por `Abre` se interpreto completo como
  `app_name` y fallo la validacion.
- Los prompts de escritura, busqueda UIA y seguridad cayeron al modelo, que
  respondio con limitaciones inventadas en lugar de ejecutar o rechazar una
  tool concreta.
- El router solo representa una accion por turno; no puede expresar
  `abrir -> observar -> confirmar -> actuar -> verificar`.
- El planificador generico termina en `run_safe_workflow`, que no implementa
  la tarea solicitada.
- Las pruebas existentes validaban componentes y mocks, no el flujo que usa el
  usuario desde el chat.

## Causa Raiz

La capa conversacional y el runtime Computer Use evolucionaron por separado.
La presencia de capabilities registradas se trato como evidencia de producto,
aunque no existia un orquestador que las encadenase desde lenguaje natural.

## Correccion Inmediata

- Los comandos simples de apertura ya no aceptan prompts compuestos como
  nombre de aplicacion.
- Los prompts reales de observacion y escritura tienen regresiones de routing.
- El roadmap reduce la madurez de Computer Use hasta que exista evidencia UAT.

## Trabajo Pendiente

La correccion inmediata evita el error y parte de las respuestas inventadas,
pero no completa el flujo solicitado. El siguiente entregable debe ser un
orquestador de tareas de Notepad con estado, identidad de ventana,
confirmaciones y verificacion posterior. Hasta entonces el hito permanece
`EN DESARROLLO`.
