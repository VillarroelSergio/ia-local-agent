# API FastAPI local-first

La API desacopla la CLI del core `LocalAgent` para futuras UIs Tauri/React, overlay Windows, voz y paneles de tools, memoria y workflows. La CLI sigue usando el mismo core; la API entra por `AgentService -> LocalAgent`.

## Levantar

```powershell
python -m src.api.main
```

En PowerShell tambien puedes usar:

```powershell
.\scripts\start-api.ps1
```

Deja esa terminal abierta. Uvicorn es el proceso servidor; si cierras o interrumpes esa ventana, la API deja de escuchar.

Por defecto escucha en `127.0.0.1:8765`. Si `API_HOST=0.0.0.0`, se ignora salvo que `API_ALLOW_NETWORK=true`.

Variables principales:

```env
LOCAL_API_KEY=local-dev-token
API_HOST=127.0.0.1
API_PORT=8765
API_ALLOWED_ORIGINS=http://127.0.0.1:1420,http://localhost:1420
API_RATE_LIMIT_PER_MINUTE=120
API_REQUEST_SIZE_LIMIT=1000000
API_DEV_MODE=true
LLM_NATIVE_TOOLS_ENABLED=false
```

Por defecto `LLM_NATIVE_TOOLS_ENABLED=false` porque muchos modelos de LM Studio no soportan tools nativas en su chat template. El chat sigue funcionando y las tools directas de la API/CLI siguen disponibles mediante endpoints o `/tool`. Activalo solo si tu modelo local soporta OpenAI tools correctamente.

## Auth

Usa `x-api-key` o `Authorization: Bearer ...`.

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8765/api/status `
  -Headers @{ "x-api-key" = "local-dev-token" }
```

Si quieres usar curl real en PowerShell, usa `curl.exe`, no `curl`, porque `curl` suele ser alias de `Invoke-WebRequest`.

`/api/health`, `/api/status` y `/api/metrics` son endpoints de observabilidad local. Tools y workflows requieren API key.

## Chat

```powershell
curl -X POST http://127.0.0.1:8765/api/chat `
  -H "content-type: application/json" `
  -H "x-api-key: local-dev-token" `
  -d '{"message":"Hola","stream":false}'
```

SSE:

```powershell
curl -N -X POST http://127.0.0.1:8765/api/chat/stream `
  -H "content-type: application/json" `
  -H "x-api-key: local-dev-token" `
  -d '{"message":"Resume mi pantalla","stream":true}'
```

Eventos emitidos: `message.started`, `message.delta`, `message.completed`, `tool.requested`, `tool.started`, `tool.completed`, `tool.confirmation_required`, `tool.failed`, `error`.

## WebSocket

Chat:

```js
const ws = new WebSocket("ws://127.0.0.1:8765/ws/chat?token=local-dev-token")
ws.onmessage = event => console.log(JSON.parse(event.data))
ws.onopen = () => ws.send(JSON.stringify({ type: "message", message: "Hola" }))
```

Eventos del sistema:

```js
const events = new WebSocket("ws://127.0.0.1:8765/ws/events?token=local-dev-token")
```

El payload incluye `request_id` y `correlation_id` para reconexión, correlación UI y cancelación. Para cancelar: `{ "type": "cancel", "request_id": "..." }`.

## Endpoints

Chat: `POST /api/chat`, `POST /api/chat/stream`, `GET/DELETE /api/chat/sessions/{id}`.

Tools: `GET /api/tools`, `GET /api/tools/{name}`, `POST /api/tools/{name}/execute`, `POST /api/tools/confirm`, `GET /api/tools/audit`.

Memoria: `GET /api/memory`, `POST /api/memory`, `GET /api/memory/search?query=...`, `DELETE /api/memory/{id}`, `POST /api/memory/rebuild`, `GET /api/memory/stats`.

Conversaciones: `GET /api/conversations`, `POST /api/conversations`, `GET/PATCH/DELETE /api/conversations/{id}`, `GET /api/conversations/{id}/messages`.

Workflows: `GET /api/workflows`, `POST /api/workflows/{name}/run`, `GET /api/workflows/runs/{id}`, `POST /api/workflows/runs/{id}/cancel`.

## Seguridad

La API es local-first: binding localhost por defecto, CORS restrictivo, API key, rate limit, límite de tamaño, errores sin stack trace en producción y auditoría JSONL para tools. Las tools de alto riesgo pasan por la política existente de `ToolExecutor`; las destructivas/admin se deniegan y las que requieren confirmación devuelven `tool.confirmation_required`.

## Troubleshooting

Si chat falla, comprueba LM Studio en `LMSTUDIO_BASE_URL` y que haya modelo cargado. Para tests o desarrollo sin embeddings remotos, usa `SEMANTIC_EMBEDDING_PROVIDER=local_hash`.
