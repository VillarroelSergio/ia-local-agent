# Pruebas end-to-end

La suite e2e valida el agente local sin depender de LM Studio real y sin tocar
carpetas sensibles del sistema.

## Ejecutar

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m pytest tests/e2e -v
```

Pytest muestra al final:

- tests pasados
- tests fallidos
- motivo de cada fallo
- traceback y acción recomendada implícita por aserción

## Seguridad

Las pruebas usan `tmp_path` y `tests/e2e` fixtures para aislar:

- SQLite temporal
- ChromaDB temporal
- manifest RAG temporal
- sandbox controlado
- provider LLM falso

No se ejecutan acciones destructivas. Las tools peligrosas se validan mediante
política de permisos, mocks o comandos de validación, no mediante operaciones
reales.

## Cobertura

- arranque del agente
- configuración segura
- conversación mockeada
- persistencia SQLite
- memoria semántica con fallback local
- registry y executor de tools
- seguridad filesystem
- seguridad PowerShell
- flujo agente + tool
- flujo agente + memoria
- smoke test CLI
- RAG básico
- no exposición de secretos
