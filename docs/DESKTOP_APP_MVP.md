# Desktop App MVP

Interfaz Tauri + React para usar el backend local-first de IA Local Agent sin duplicar logica del agente en el frontend.

## Arranque

Desde la raiz del proyecto, primero arranca la API:

```powershell
python -m src.api.main
```

O usa el script del repo:

```powershell
.\scripts\start-api.ps1
```

Despues arranca la app desktop:

```powershell
cd ui\desktop
npm install
npm run tauri:dev
```

La UI asume por defecto:

```text
VITE_API_BASE_URL=http://127.0.0.1:8765
VITE_LOCAL_API_TOKEN=local-dev-token
```

Puedes crear `ui/desktop/.env` a partir de `.env.example` si cambias `LOCAL_API_KEY` o el puerto de la API.

## Endpoints Usados

- `GET /api/health`
- `GET /api/status`
- `GET /api/metrics`
- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{id}/messages`
- `PATCH /api/conversations/{id}`
- `DELETE /api/conversations/{id}`
- `GET /api/tools`
- `GET /api/tools/{name}`
- `GET /api/tools/audit`
- `POST /api/tools/{name}/execute`
- `POST /api/tools/confirm`
- `GET /api/memory/stats`
- `POST /api/memory/rebuild`
- `GET /api/memory/search?query=...`
- `GET /api/settings`
- `PATCH /api/settings`
- `WS /ws/chat?token=...`
- `WS /ws/events?token=...`

## Settings

El frontend no escribe `.env` directamente. Los cambios pasan por `GET /api/settings` y `PATCH /api/settings`.

`LMSTUDIO_API_KEY` se devuelve enmascarada. Si la UI envia el valor enmascarado de vuelta, el backend lo ignora para no sobrescribir el secreto real con asteriscos.

Los cambios se persisten en el `.env` del proyecto y aplican de forma completa al reiniciar el backend. El runtime actual mantiene instancias cacheadas de `LocalAgent`, asi que no se fuerza hot reload del agente en este MVP.

## Funcionalidad MVP

- Ventana unica con sidebar de conversaciones, chat central y panel derecho de tools/timeline/memoria.
- Chat por `WS /ws/chat`; si falla, fallback a SSE `POST /api/chat/stream`; si tambien falla, fallback a `POST /api/chat`.
- Streaming incremental de texto.
- Cancelacion por WebSocket cuando existe `request_id`; en fallback SSE se aborta la request local.
- Historial persistente desde SQLite via endpoints de conversaciones.
- Panel de tools conectado a `ToolExecutor` via API.
- Modal global para confirmaciones de tools.
- Timeline tecnico desde eventos de chat y `WS /ws/events`.
- Settings basicos de LM Studio, contexto, tools y RAG.
- Estado de backend, provider, modelo, memoria y metricas basicas.

## Limitaciones

- El backend Python se arranca externamente; Tauri aun no lo empaqueta ni lo lanza.
- No hay adjuntos ni gestor visual completo de documentos RAG.
- La confirmacion de tools se resuelve mediante el endpoint HTTP existente. El WebSocket de chat solo acepta cancelacion y recibe eventos.
- Los settings persisten en `.env`, pero requieren reiniciar backend para reconstruir provider, memoria, contexto y tool executor.
- El build Tauri queda preparado para Windows, pero requiere Node/npm, Rust y dependencias Tauri instaladas en la maquina.

## Proximos Pasos

- Empaquetar backend Python con Tauri.
- Docker futuro para el runtime local.
- Gestor visual RAG con ingestion y estado por documento.
- Adjuntos en chat.
- Overlay de escritorio.
- Voz.
