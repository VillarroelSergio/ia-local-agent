# Desktop App MVP

Interfaz Tauri + React para usar el backend local-first de IA Local Agent sin duplicar logica del agente en el frontend.

## Modo Desarrollo

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

## Modo App Windows

La app empaquetada arranca la UI Tauri y gestiona el backend Python como sidecar. Para generar el instalador:

```powershell
.\scripts\build-windows-app.ps1
```

El build completo incrementa automaticamente la version `patch` definida en `VERSION`. Para saltos de release mayores:

```powershell
.\scripts\build-windows-app.ps1 -VersionPart minor
.\scripts\build-windows-app.ps1 -VersionPart major
```

Resultado esperado:

```text
ui\desktop\src-tauri\target\release\bundle\nsis\IA Local Agent Setup.exe
```

O:

```text
ui\desktop\src-tauri\target\release\bundle\msi\IA Local Agent.msi
```

El sidecar usa `python -m src.api.desktop_entry` empaquetado con PyInstaller. En modo desktop fuerza `API_HOST=127.0.0.1` y guarda datos modificables bajo `AppData\Local\IA Local Agent`, no dentro de `Program Files`.

Detalles completos: [WINDOWS_APP_BUILD.md](WINDOWS_APP_BUILD.md).

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

- En desarrollo, el backend Python se sigue arrancando externamente.
- En app empaquetada, Tauri arranca o reutiliza el backend local en `127.0.0.1:8765`.
- LM Studio sigue arrancandose aparte.
- No hay adjuntos ni gestor visual completo de documentos RAG.
- La confirmacion de tools se resuelve mediante el endpoint HTTP existente. El WebSocket de chat solo acepta cancelacion y recibe eventos.
- Los settings persisten en `.env`, pero requieren reiniciar backend para reconstruir provider, memoria, contexto y tool executor.
- El token local de MVP es `local-dev-token`; debe evolucionar a token generado por instalacion.
- ChromaDB, tokenizers o sentence-transformers pueden requerir ajustes adicionales de PyInstaller segun version instalada.

## Proximos Pasos

- Endurecer token local generado por instalacion.
- Docker futuro para el runtime local.
- Gestor visual RAG con ingestion y estado por documento.
- Adjuntos en chat.
- Overlay de escritorio.
- Voz.
