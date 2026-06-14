# Playbook: Depurar Overlay Windows

## Objetivo

Diagnosticar problemas del overlay Tauri: hotkey, ventana activa, contexto, OCR bajo demanda o posicionamiento.

## Repositorio

Proyecto:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Pasos

1. Arrancar backend:

```powershell
venv\Scripts\python.exe -m src.api.main
```

2. Arrancar desktop:

```powershell
cd ui\desktop
npm run tauri:dev
```

3. Probar hotkey:

```text
Ctrl + Alt + Space
```

4. Probar endpoint de ventana activa:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/system/active-window
```

5. Probar con varias apps:

- VS Code.
- Navegador.
- Explorer.
- App minimizada.
- Ventana sensible o simulada.

## Reglas De Seguridad

- No capturar pantalla automaticamente.
- No ejecutar OCR continuo.
- No automatizar UAC, login, password managers ni campos password.
- Pedir confirmacion para OCR, captura o accion de alto riesgo.

## Archivos Clave

- `docs/OVERLAY_WINDOWS.md`
- `src/api/routes/system.py`
- `src/os_integration/`
- `src/windows/`
- `ui/desktop/src/features/overlay/OverlayView.tsx`
- `ui/desktop/src-tauri/src/lib.rs`

## Agentes

- `windows-overlay-agent.md`
- `frontend-tauri-agent.md`
- `qa-test-agent.md`
