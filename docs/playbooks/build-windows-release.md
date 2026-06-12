# Playbook: Build Windows Release

## Objetivo

Generar una app Windows instalable con frontend Tauri y backend Python como sidecar.

## Repositorio

Proyecto:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Verificacion Rapida

```powershell
venv\Scripts\python.exe -m src.api.desktop_entry
```

En otra terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health
```

## Build Backend

```powershell
.\scripts\build-backend.ps1
```

Salida esperada:

```text
dist\ia-local-agent-api.exe
ui\desktop\src-tauri\binaries\ia-local-agent-api-x86_64-pc-windows-msvc.exe
```

## Build App

Para verificacion sin cambiar version:

```powershell
.\scripts\build-windows-app.ps1 -NoVersionBump
```

Para release patch:

```powershell
.\scripts\build-windows-app.ps1
```

## Validaciones

- `npm run build` pasa.
- `cargo check` pasa.
- El instalador NSIS o MSI se genera.
- La app instalada abre.
- Chat, historial, tools, settings y timeline funcionan.
- LM Studio cerrado muestra error controlado.

## No Empaquetar

- `.env`
- `data`
- Chroma
- SQLite
- Logs
- Cualquier secreto local

## Agentes

- `build-release-agent.md`
- `qa-test-agent.md`
