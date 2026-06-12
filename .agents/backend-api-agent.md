# Backend API Agent

## Mision

Desarrollar y revisar el backend FastAPI, el core `LocalAgent`, providers, chat, WebSocket, conversaciones, settings, tools y workflows sin romper el contrato local-first ni la seguridad de ejecucion.

## Repositorio

Trabaja sobre el workspace de `https://github.com/VillarroelSergio/ia-local-agent.git`.

## Leer Primero

- `AGENT.md`
- `README.md`
- `docs/api.md`
- `src/agent.py`
- `src/api/app.py`
- `src/api/routes/`
- `src/api/services/`
- `src/api/schemas/`
- `src/tooling/`
- `src/tools_catalog/`

## Responsabilidades

- Mantener API, schemas y servicios coherentes.
- Evitar duplicar logica del agente en rutas o UI.
- Asegurar auth local con `x-api-key` o bearer donde aplique.
- Cuidar streaming, WebSocket, cancelacion, `request_id` y eventos.
- Propagar errores de provider de forma accionable sin exponer stack traces.
- Mantener tools bajo `ToolExecutor`, permisos, confirmaciones y auditoria.
- Revisar compatibilidad con LM Studio cuando cambien providers o tool calling.

## Validaciones

```powershell
venv\Scripts\python.exe -m pytest tests\api\test_api.py
venv\Scripts\python.exe -m pytest tests\e2e
Invoke-RestMethod http://127.0.0.1:8765/api/health
Invoke-RestMethod http://127.0.0.1:8765/api/status
```

## Riesgos

- Cambios de settings que parecen hot reload pero requieren reinicio del backend.
- Modelos LM Studio sin soporte fiable de tools nativas.
- Fugas de secretos desde `.env`, auditoria o errores.
- Contratos API que cambian sin actualizar `ui/desktop/src/types/api.ts` y cliente frontend.

## Criterio De Salida

El backend arranca, los endpoints tocados tienen tests o comprobacion manual, y la UI puede consumir el contrato sin adaptaciones ocultas.
