# Playbook: Anadir Tool

## Objetivo

Crear una tool local segura y auditable para el agente o la API.

## Repositorio

Proyecto:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Pasos

1. Revisar tools existentes:

```text
src/tools_catalog/
src/tooling/
```

2. Definir schema de entrada/salida.
3. Registrar la tool en el registry correspondiente.
4. Clasificar riesgo:

- Lectura segura.
- Requiere confirmacion.
- Denegada o no soportada.

5. Pasar por `ToolExecutor`, permisos y auditoria.
6. Emitir errores seguros y accionables.
7. Anadir tests de registry, permiso y ejecucion.
8. Actualizar UI si debe aparecer en panel de tools.

## Seguridad

- No saltarse `ToolExecutor`.
- No ejecutar acciones destructivas sin confirmacion o denegacion.
- No leer secretos, credenciales, perfiles de navegador ni AppData sensible.
- No automatizar UAC, login o password managers.

## Pruebas

```powershell
venv\Scripts\python.exe -m pytest tests\e2e\test_06_tool_registry.py
venv\Scripts\python.exe -m pytest tests\e2e\test_07_tool_executor_confirmation.py
venv\Scripts\python.exe -m pytest tests\api\test_api.py
```

## Agentes

- `backend-api-agent.md`
- `windows-overlay-agent.md` si toca Windows
- `qa-test-agent.md`
