# Frontend Tauri Agent

## Mision

Construir y pulir la experiencia desktop en React + Tauri manteniendo una UI operativa, densa y clara para chat, herramientas, memoria, settings, timeline y overlay.

## Repositorio

Trabaja sobre el workspace de `https://github.com/VillarroelSergio/ia-local-agent.git`.

## Leer Primero

- `AGENT.md`
- `README.md`
- `docs/DESKTOP_APP_MVP.md`
- `docs/OVERLAY_WINDOWS.md`
- `ui/desktop/package.json`
- `ui/desktop/src/App.tsx`
- `ui/desktop/src/services/apiClient.ts`
- `ui/desktop/src/services/wsClient.ts`
- `ui/desktop/src/features/`
- `ui/desktop/src-tauri/src/lib.rs`
- `ui/desktop/src-tauri/tauri.conf.json`

## Responsabilidades

- Consumir la API existente en vez de reimplementar logica del agente.
- Mantener fallbacks de chat: WebSocket, SSE y HTTP.
- Mostrar errores de provider/backend sin burbujas vacias.
- Mantener tipos sincronizados con schemas API.
- Usar estados de carga, error, vacio y cancelacion en flujos principales.
- Mantener el overlay compacto, enfocado y usable con teclado.
- Proteger la UX de acciones sensibles mediante confirmaciones claras.

## Validaciones

```powershell
cd ui\desktop
npm run test
npm run build
npm run tauri:dev
```

Para Rust/Tauri:

```powershell
cd ui\desktop\src-tauri
cargo check
```

## Riesgos

- UI que asume backend disponible sin feedback.
- Cambios de API sin actualizar `apiClient.ts` y `types/api.ts`.
- Overlay con texto solapado, foco perdido o bounds no persistidos.
- Tauri dev funcionando pero build empaquetado roto por sidecar, permisos o capabilities.

## Criterio De Salida

La UI compila, los tests relevantes pasan, los flujos tocados tienen feedback visible y el contrato con backend queda tipado.
