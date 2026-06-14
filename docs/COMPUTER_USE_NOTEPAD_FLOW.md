# Computer Use Notepad Flow

Diseno aprobado el 14 de junio de 2026 por la ruta:

```text
CEO -> Planificador -> Jefe de Ingenieria -> Disenador
-> Backend API / Windows Overlay -> Constructor -> Bugs -> QA / Testeo
```

## Objetivo

El chat debe convertir un objetivo natural de Notepad en una sesion Computer
Use observable. El modelo no decide si una tool existe ni puede responder con
capacidades inventadas.

## Contrato

```text
prompt -> intent determinista -> sesion -> plan -> ejecutar
       -> esperar confirmacion -> reanudar -> observar -> verificar
```

Planes soportados:

- Abrir Notepad y observar su ventana mediante UIA.
- Escribir texto entre comillas en el documento activo.
- Invocar `Guardar` mediante UIA cuando se solicite explicitamente.

Las acciones `fill_text_field` y `click_ui_control` mantienen su confirmacion
interna. La tool `computer_use` no pide una confirmacion adicional: el motor
pausa justo antes de la accion sensible.

## Seguridad

- Una apertura solo se acepta si aparece una unica ventana nueva verificable.
- Escritura y click validan foco, HWND, PID, titulo e identidad UIA.
- Cambios de foco o superficies sensibles cancelan la accion.
- El texto de escritura no se publica en eventos ni confirmaciones.
- Un objetivo no soportado falla de forma explicita; no se simula.

## Limitaciones Vigentes

- El flujo no crea todavia un archivo temporal asociado a una instancia.
- No rastrea ni limpia recursos creados durante una conversacion.
- No crea formularios de password para UAT.
- La evidencia sobre Windows real corresponde exclusivamente al UAT manual
  realizado por el usuario.
