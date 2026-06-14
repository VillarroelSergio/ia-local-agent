# Overlay Change Template

## Objetivo

Describe el cambio en overlay, hotkey, ventana activa, OCR, captura o workflow Windows.

## Repositorio

Trabajar en:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Agentes

- Principal: `windows-overlay-agent.md`
- UI: `frontend-tauri-agent.md`
- QA: `qa-test-agent.md`

## Contexto A Leer

- `docs/OVERLAY_WINDOWS.md`
- `docs/WINDOWS_OS_AGENT_ARCHITECTURE.md`
- `src/api/routes/system.py`
- `src/os_integration/`
- `src/windows/`
- `ui/desktop/src/features/overlay/OverlayView.tsx`
- `ui/desktop/src-tauri/src/lib.rs`

## Seguridad

- No captura automatica.
- No OCR continuo.
- No automatizar UAC/login/password managers.
- Confirmacion para acciones de alto riesgo.
- Ventanas sensibles no exponen titulo/contenido.

## Pruebas Manuales

- VS Code.
- Navegador.
- Explorer.
- App minimizada.
- Multi-monitor si esta disponible.
- DPI alto si esta disponible.

## Pruebas Automatizadas

Consultar `docs/TESTING_MATRIX.md`.

## Criterio De Salida

El overlay funciona en el caso principal y falla con mensajes seguros en casos bloqueados o no soportados.
