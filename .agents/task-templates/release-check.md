# Release Check Template

## Release

- Version:
- Tipo: patch/minor/major/verificacion
- Objetivo:

## Repositorio

Trabajar en:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Agentes

- Principal: `build-release-agent.md`
- Validacion: `qa-test-agent.md`

## Checklist

- `VERSION` revisado.
- `ui/desktop/package.json` sincronizado si aplica.
- `ui/desktop/src-tauri/Cargo.toml` sincronizado si aplica.
- `ui/desktop/src-tauri/tauri.conf.json` sincronizado si aplica.
- API desktop arranca.
- Backend sidecar se genera.
- Frontend compila.
- Cargo check pasa.
- Instalador se genera.
- Datos privados no se empaquetan.

## Comandos

```powershell
venv\Scripts\python.exe -m src.api.desktop_entry
.\scripts\build-backend.ps1
cd ui\desktop
npm run build
cd src-tauri
cargo check
cd ..\..\..
.\scripts\build-windows-app.ps1 -NoVersionBump
```

## Salidas

- Backend:
- NSIS:
- MSI:

## Riesgos

- PyInstaller:
- Tauri capabilities:
- Puerto 8765:
- LM Studio externo:
