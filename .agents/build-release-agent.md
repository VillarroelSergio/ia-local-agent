# Build Release Agent

## Mision

Preparar builds Windows reproducibles de IA Local Agent con backend Python empaquetado como sidecar Tauri, respetando versionado, datos locales y seguridad.

## Repositorio

Trabaja sobre el workspace de `https://github.com/VillarroelSergio/ia-local-agent.git`.

## Leer Primero

- `AGENT.md`
- `README.md`
- `docs/WINDOWS_APP_BUILD.md`
- `scripts/build-backend.ps1`
- `scripts/build-windows-app.ps1`
- `VERSION`
- `ui/desktop/package.json`
- `ui/desktop/src-tauri/Cargo.toml`
- `ui/desktop/src-tauri/tauri.conf.json`
- `src/api/desktop_entry.py`

## Responsabilidades

- Verificar requisitos: Python deps, Node/npm, Rust/Cargo, Tauri v2 y LM Studio externo.
- Mantener sincronizado versionado entre `VERSION`, package, Cargo y Tauri config.
- Confirmar que el sidecar se genera con target triple correcto.
- No empaquetar `.env`, `data`, Chroma, SQLite, logs ni datos privados.
- Validar lifecycle: detectar backend existente, arrancar sidecar, cerrar sidecar propio.
- Usar `-NoVersionBump` para builds de verificacion cuando no sea release.

## Validaciones

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

## Checklist Release

- API responde `/api/health`.
- Backend empaquetado responde `/api/health`.
- `npm run build` pasa.
- `cargo check` pasa.
- Tauri detecta o arranca backend.
- Chat, historial, tools, settings y timeline funcionan.
- LM Studio cerrado produce error visible.
- Instalador NSIS/MSI se genera.

## Riesgos

- ChromaDB, tokenizers o sentence-transformers pueden requerir ajustes PyInstaller.
- Puerto `8765` ocupado por proceso ajeno.
- Token `local-dev-token` es MVP y debe evolucionar.
- Cambios de capabilities Tauri pueden romper APIs en runtime empaquetado.

## Criterio De Salida

Existe instalador o build verificable, con rutas de salida documentadas y sin incluir datos privados.
