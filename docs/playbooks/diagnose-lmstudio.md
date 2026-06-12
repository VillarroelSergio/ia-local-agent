# Playbook: Diagnosticar LM Studio

## Objetivo

Resolver fallos de chat, respuestas vacias o errores de provider cuando IA Local Agent usa LM Studio.

## Repositorio

Proyecto:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Pasos

1. Confirmar que LM Studio esta abierto.
2. Confirmar que el servidor OpenAI-compatible esta activo en:

```text
http://127.0.0.1:1234/v1
```

3. Ver modelos cargados:

```powershell
Invoke-RestMethod http://127.0.0.1:1234/v1/models
```

4. Revisar `.env`:

```env
DEFAULT_PROVIDER=lmstudio
DEFAULT_MODEL=<id exacto del modelo cargado>
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_API_KEY=lm-studio
```

5. Consultar diagnostico del backend si esta disponible:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/system/lmstudio
```

6. Probar chat directo:

```powershell
$body = @{ message = "Responde solo OK"; use_tools = $false; stream = $false } | ConvertTo-Json
Invoke-RestMethod `
  -Uri http://127.0.0.1:8765/api/chat `
  -Method Post `
  -ContentType "application/json" `
  -Headers @{ "x-api-key" = "local-dev-token" } `
  -Body $body
```

## Causas Frecuentes

- LM Studio cerrado.
- Servidor local no iniciado.
- `DEFAULT_MODEL` no coincide con el ID real.
- Modelo sin soporte fiable para tools nativas.
- Backend necesita reinicio tras cambiar `.env`.

## Agentes

- `backend-api-agent.md`
- `frontend-tauri-agent.md` si el problema solo se ve en UI
- `qa-test-agent.md`
