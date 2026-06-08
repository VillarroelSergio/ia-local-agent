# Overlay Windows

Base tecnica para convertir la app desktop en una ventana flotante segura sobre Windows.

## Objetivo

El overlay debe permitir invocar el agente desde el escritorio, leer contexto seguro de la ventana activa y pedir confirmaciones sin capturar pantalla ni automatizar acciones sensibles por defecto.

## Estado actual

- Endpoint seguro: `GET /api/system/active-window`.
- Vista compacta React activable con `?mode=overlay`.
- Ventana Tauri dedicada `overlay`, oculta al arrancar.
- Shortcut global `Ctrl+Alt+Space` para mostrar u ocultar el overlay.
- Chat reutiliza el flujo actual por WebSocket, SSE y fallback HTTP.
- La ventana activa se consulta como metadata: titulo, proceso, pid, estado y monitor.
- Si la politica OS bloquea una ventana sensible, el endpoint oculta el titulo.

## Alcance MVP

1. Shortcut global `Ctrl+Alt+Space`.
2. Ventana flotante compacta Tauri.
3. Contexto de ventana activa mediante metadata segura.
4. Confirmaciones seguras para tools y workflows.
5. Conexion con `WS /ws/events` para reflejar actividad reciente.

## Seguridad

El overlay no debe:

- Capturar pantalla automaticamente.
- Ejecutar OCR continuo.
- Automatizar UAC, pantallas admin, login, password managers o gestores de credenciales.
- Escribir texto en campos de password.
- Persistir screenshots u OCR de ventanas sensibles.

Las acciones de alto riesgo deben pasar por `ToolExecutor`, `OSSecurityPolicy` y confirmacion humana.

## Contrato API

```http
GET /api/system/active-window
```

Respuesta:

```json
{
  "available": true,
  "allowed": true,
  "reason": "Permitido por politica OS.",
  "window": {
    "handle": 123456,
    "title": "Visual Studio Code",
    "process_name": "Code.exe",
    "pid": 1234,
    "state": "normal",
    "monitor_index": 0,
    "sensitive": false
  }
}
```

Si la ventana es sensible, `allowed` sera `false` y el titulo no se devolvera.

## Activacion frontend

En desarrollo, abrir la app con:

```text
http://localhost:1420/?mode=overlay
```

En Tauri, la ventana dedicada se crea con label `overlay`, dimensiones iniciales `420x560`, `always-on-top`, `skip_taskbar` y carga `index.html?mode=overlay`.

## Proximos pasos

1. Persistir posicion y tamano del overlay.
2. Hacer configurable el shortcut global.
3. Mostrar confirmaciones en una superficie no tapable por contenido web externo.
4. Anadir contexto opcional bajo demanda: OCR o screenshot solo tras accion explicita.
5. Anadir controles de minimizar/cerrar propios si se retiran decoraciones nativas.
