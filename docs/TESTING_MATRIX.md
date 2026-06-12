# Testing Matrix

Matriz para elegir pruebas segun el area tocada. Usa la prueba mas pequena que cubra el riesgo, y amplia cuando cambien contratos, seguridad o build.

## Backend API

| Cambio | Pruebas minimas | Pruebas extra |
| --- | --- | --- |
| Rutas API | `venv\Scripts\python.exe -m pytest tests\api\test_api.py` | Tests e2e del flujo afectado |
| Chat o streaming | `tests\api\test_api.py` | `tests\e2e\test_03_conversation_mocked.py`, pruebas manuales WS/SSE |
| WebSocket/cancelacion | `tests\api\test_api.py` | Prueba manual desde desktop |
| Settings | `tests\api\test_api.py` | Verificar que `.env` no pierde secretos enmascarados |
| Tools | `tests\e2e\test_06_tool_registry.py`, `tests\e2e\test_07_tool_executor_confirmation.py` | Auditoria y confirmaciones manuales |
| Provider LM Studio | `tests\e2e\test_18_lmstudio_message_safety.py` | `Invoke-RestMethod http://127.0.0.1:1234/v1/models` |

## Frontend React

| Cambio | Pruebas minimas | Pruebas extra |
| --- | --- | --- |
| Componentes UI | `cd ui\desktop; npm run test` | Screenshot/manual si hay layout complejo |
| Cliente API/tipos | `npm run test`, `npm run build` | Probar contra backend real |
| Chat UI | `npm run test`, `npm run build` | Manual WS/SSE/HTTP fallback |
| Settings/memoria | `npm run test`, `npm run build` | Backend real con `/api/settings` y `/api/memory/stats` |
| Overlay React | `npm run build` | Manual `?mode=overlay` y Tauri overlay |

## Tauri/Rust/Desktop

| Cambio | Pruebas minimas | Pruebas extra |
| --- | --- | --- |
| `src-tauri/src/lib.rs` | `cd ui\desktop\src-tauri; cargo check` | `npm run tauri:dev` |
| Capabilities/permisos | `cargo check`, `npm run build` | Probar app empaquetada si afecta release |
| Sidecar backend | `venv\Scripts\python.exe -m src.api.desktop_entry` | `.\scripts\build-backend.ps1` |
| Lifecycle desktop | `cargo check`, `npm run tauri:dev` | Abrir dos instancias y puerto ocupado |

## Overlay Y Windows Runtime

| Cambio | Pruebas minimas | Pruebas extra |
| --- | --- | --- |
| Ventana activa/HWND | `tests\e2e\test_17_windows_task_runtime.py` | Manual con VS Code, navegador, Explorer |
| OCR/captura | Tests runtime si existen | Manual bajo demanda con ventana permitida |
| Hotkeys | `cargo check` | Manual `Ctrl+Alt+Space` |
| Politicas OS | Tests e2e de seguridad | Manual con ventanas sensibles simuladas |

## RAG Y Memoria

| Cambio | Pruebas minimas | Pruebas extra |
| --- | --- | --- |
| Memoria semantica | `tests\e2e\test_05_semantic_memory.py` | API `/api/memory/stats` |
| RAG ingestion/search | `tests\e2e\test_13_rag_basic.py` | Indexar carpeta de prueba |
| Seguridad RAG | `tests\e2e\test_08_filesystem_security.py`, `tests\e2e\test_14_secret_exposure.py` | Revisar `safe_source` en UI |
| Panel RAG UI | `npm run test`, `npm run build` | Backend real con docs indexados |

## Build Y Release

| Cambio | Pruebas minimas | Pruebas extra |
| --- | --- | --- |
| Scripts build | `.\scripts\build-windows-app.ps1 -NoVersionBump` | Instalar y abrir app |
| Versionado | Revisar `VERSION`, package, Cargo, Tauri config | Build completo |
| PyInstaller/backend | `.\scripts\build-backend.ps1` | Ejecutar `.exe` y pedir `/api/health` |
| Instalador | Build Windows | Smoke test post-instalacion |

## Smoke Test Manual

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health
Invoke-RestMethod http://127.0.0.1:8765/api/status
Invoke-RestMethod http://127.0.0.1:1234/v1/models
```

Flujos manuales:

- Chat responde o muestra error de LM Studio claro.
- Historial carga.
- Tools panel carga.
- Settings carga y no sobrescribe secretos enmascarados.
- Overlay abre/cierra y muestra contexto permitido.
- RAG stats carga si esta habilitado.
