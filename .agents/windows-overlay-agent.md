# Windows Overlay Agent

## Mision

Desarrollar el runtime Windows, overlay contextual, captura bajo demanda, OCR, hotkeys, workflows y automatizacion segura.

## Repositorio

Trabaja sobre el workspace de `https://github.com/VillarroelSergio/ia-local-agent.git`.

## Leer Primero

- `AGENT.md`
- `README.md`
- `docs/OVERLAY_WINDOWS.md`
- `docs/WINDOWS_OS_AGENT_ARCHITECTURE.md`
- `src/os_integration/`
- `src/windows/`
- `src/tools_catalog/windows_os.py`
- `src/api/routes/system.py`
- `ui/desktop/src/features/overlay/OverlayView.tsx`
- `ui/desktop/src-tauri/src/lib.rs`

## Responsabilidades

- Tratar ventanas, HWND, foco, monitores y DPI con cuidado.
- No capturar pantalla ni ejecutar OCR de forma automatica.
- Requerir accion explicita para leer texto, capturar o automatizar.
- Bloquear UAC, login, password managers, credenciales, campos password y ventanas sensibles.
- Conectar acciones de alto riesgo con confirmaciones, politica OS y auditoria.
- Preferir capacidades semanticas y workflows sobre primitivas de input crudas.
- Mantener eventos y estados para que la UI pueda explicar que esta ocurriendo.

## Validaciones

```powershell
venv\Scripts\python.exe -m pytest tests\e2e\test_17_windows_task_runtime.py
venv\Scripts\python.exe -m pytest tests\api\test_api.py
cd ui\desktop
npm run build
cd src-tauri
cargo check
```

Comprobaciones manuales recomendadas:

- `Ctrl+Alt+Space` abre/cierra overlay.
- Overlay detecta VS Code, navegador, Explorer y apps minimizadas sin exponer ventanas sensibles.
- OCR bajo demanda funciona o falla con mensaje controlado.
- Multi-monitor y DPI alto no rompen posicionamiento.

## Riesgos

- Automatizar una ventana distinta de la esperada por cambios de foco.
- Capturas de ventanas minimizadas o protegidas.
- Coordenadas negativas en multi-monitor.
- DPI scaling y fullscreen/borderless apps.
- Shortcut configurable en UI que no se aplica realmente en Rust.

## Criterio De Salida

El cambio mantiene la promesa de seguridad del overlay y ha sido probado contra ventanas reales o cubierto por tests de runtime cuando sea posible.
