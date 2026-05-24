# Windows App Build

Guia para generar una app Windows instalable de IA Local Agent con UI Tauri y backend Python FastAPI empaquetado como sidecar.

## Requisitos

- Windows.
- Python con las dependencias de `requirements.txt`.
- Node.js y npm.
- Rust y Cargo.
- Dependencias de Tauri v2 para Windows.
- LM Studio instalado y arrancado aparte, con servidor local en `http://127.0.0.1:1234/v1`.

## Modo Desarrollo

Desde la raiz del proyecto:

```powershell
python -m src.api.main
```

En otra terminal:

```powershell
cd ui\desktop
npm install
npm run tauri:dev
```

El modo desarrollo sigue esperando que la API exista en:

```text
http://127.0.0.1:8765
```

Puedes cambiarlo en desarrollo con `VITE_API_BASE_URL`. En produccion empaquetada la UI usa siempre `http://127.0.0.1:8765`.

## Modo Backend Desktop

El entrypoint usado por el sidecar es:

```powershell
python -m src.api.desktop_entry
```

Este modo fuerza:

```text
APP_ENV=desktop
API_HOST=127.0.0.1
API_PORT=8765
LOCAL_API_KEY=local-dev-token
API_ALLOWED_ORIGINS=http://127.0.0.1:1420,http://localhost:1420,tauri://localhost,http://tauri.localhost
```

Para el MVP se permite `local-dev-token`. Debe evolucionar a un token local generado durante instalacion o primer arranque.

## Datos Locales

En modo desktop empaquetado, los datos modificables viven en:

```text
C:\Users\<usuario>\AppData\Local\IA Local Agent\
```

Incluye:

```text
data\
logs\
conversations.sqlite3
chroma\
rag_manifest.json
.env
```

La app no debe escribir datos modificables dentro de `Program Files`.

## Build Backend

```powershell
.\scripts\build-backend.ps1
```

Genera:

```text
dist\ia-local-agent-api.exe
ui\desktop\src-tauri\binaries\ia-local-agent-api-x86_64-pc-windows-msvc.exe
```

Tauri v2 declara el sidecar como `binaries/ia-local-agent-api`, pero el archivo real debe incluir el target triple de Rust.

El build no incluye deliberadamente:

```text
.env
data\
chroma\
conversations.sqlite3
rag_manifest.json
logs\
```

## Build App Windows

```powershell
.\scripts\build-windows-app.ps1
```

El script:

1. Empaqueta el backend Python.
2. Instala dependencias frontend si falta `node_modules`.
3. Ejecuta `npm run tauri:build`.
4. Muestra la ruta del instalador.

Resultado esperado:

```text
ui\desktop\src-tauri\target\release\bundle\nsis\IA Local Agent Setup.exe
```

O:

```text
ui\desktop\src-tauri\target\release\bundle\msi\IA Local Agent.msi
```

## Lifecycle Desktop

Al abrir la app empaquetada, Tauri:

1. Consulta `http://127.0.0.1:8765/api/health`.
2. Si responde IA Local Agent, reutiliza ese backend.
3. Si no responde, arranca el sidecar `ia-local-agent-api`.
4. Espera a que `/api/health` responda.
5. Si el puerto esta ocupado por otro proceso, informa error.
6. Al cerrar la ventana, termina el sidecar si fue creado por Tauri.

## Seguridad

- La API desktop se fuerza a `127.0.0.1`.
- No se usa `0.0.0.0` en modo desktop.
- No se empaquetan `.env`, `data`, SQLite, Chroma ni logs privados.
- No se relaja CORS globalmente.
- La autenticacion local con `x-api-key` se mantiene.
- Los errores del backend pasan por middleware seguro; la UI no debe mostrar stack traces.

## Limitaciones Actuales

- LM Studio sigue arrancandose aparte.
- ChromaDB, tokenizers o sentence-transformers pueden requerir ajustes adicionales de PyInstaller segun version instalada.
- Algunos cambios de settings requieren reiniciar el backend.
- El token local de MVP debe evolucionar a token generado por instalacion.
- El cierre limpio mata el sidecar creado por Tauri, pero no termina backends externos que el usuario ya tuviera abiertos.

## Checklist Manual

1. `python -m src.api.desktop_entry` arranca la API.
2. `GET /api/health` responde.
3. `scripts/build-backend.ps1` genera `ia-local-agent-api.exe`.
4. Ejecutar `ia-local-agent-api.exe` responde `/api/health`.
5. `npm run tauri:dev` funciona.
6. Tauri puede arrancar o detectar el backend.
7. Al cerrar la app, el backend creado por Tauri se cierra.
8. Abrir la app dos veces no crea conflictos graves.
9. Chat funciona.
10. Historial funciona.
11. Tools panel carga.
12. Settings carga.
13. Timeline recibe eventos.
14. Si LM Studio esta cerrado, la UI muestra error controlado.
15. Si el puerto 8765 esta ocupado, la app informa o reutiliza backend sano.
16. `scripts/build-windows-app.ps1` genera instalador.
17. Instalar y abrir desde menu inicio funciona.
