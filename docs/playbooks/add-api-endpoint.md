# Playbook: Anadir Endpoint API

## Objetivo

Crear o modificar un endpoint FastAPI sin romper contratos, auth ni consumidores frontend.

## Repositorio

Proyecto:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Pasos

1. Leer `docs/api.md`.
2. Identificar ruta en `src/api/routes/`.
3. Definir o actualizar schema en `src/api/schemas/`.
4. Implementar logica en `src/api/services/` si no pertenece a la ruta.
5. Aplicar auth y dependencias desde `src/api/dependencies.py`.
6. Actualizar frontend si consume el endpoint:

```text
ui/desktop/src/services/apiClient.ts
ui/desktop/src/types/api.ts
```

7. Anadir o actualizar tests.
8. Actualizar `docs/api.md` si cambia el contrato publico.

## Pruebas

```powershell
venv\Scripts\python.exe -m pytest tests\api\test_api.py
```

Si afecta UI:

```powershell
cd ui\desktop
npm run build
```

## Agentes

- `backend-api-agent.md`
- `frontend-tauri-agent.md` si hay UI
- `qa-test-agent.md`
