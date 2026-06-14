# User Acceptance Test Template

## Objetivo

Validar una funcionalidad nueva y regresiones relacionadas mediante prompts escritos por el usuario al agente. El usuario no debe seleccionar tools ni operar paneles internos para completar la prueba.

## Repositorio

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Agentes

- Principal: `user-acceptance-test-agent.md`
- QA automatizado: `qa-test-agent.md`
- Correctores potenciales:
  - `backend-api-agent.md`
  - `frontend-tauri-agent.md`
  - `windows-overlay-agent.md`
  - `rag-memory-agent.md`
  - `build-release-agent.md`

## Precondiciones

- Rama/commit:
- Backend arrancado:
- App desktop arrancada:
- LM Studio:
- Modelo cargado:
- Variables `.env` relevantes:

## Pruebas Nuevas

| ID | Caso | Prompt que escribe el usuario | Resultado esperado | Decision interna esperada | Evidencia si falla |
| --- | --- | --- | --- | --- |
| NEW-01 |  |  |  |  |  |

## Regresion

| ID | Caso | Prompt que escribe el usuario | Resultado esperado | Decision interna esperada | Evidencia si falla |
| --- | --- | --- | --- | --- |
| REG-01 |  |  |  |  |  |

## Seguridad

| ID | Caso | Prompt que escribe el usuario | Resultado esperado | Decision interna esperada | Evidencia si falla |
| --- | --- | --- | --- | --- |
| SEC-01 |  |  |  |  |  |

## Formato Para Que El Usuario Devuelva Resultados

```text
Caso:
Resultado: PASS / FAIL / BLOCKED / NEEDS_INFO
Que ocurrio:
Prompt exacto:
Evidencia:
Notas:
```

## Enrutamiento Tras Resultados

| Sintoma | Agente corrector |
| --- | --- |
| Error HTTP, endpoint, auth, schema | `backend-api-agent.md` |
| UI rota, boton no responde, texto solapado | `frontend-tauri-agent.md` |
| Ventana activa, OCR, overlay, Computer Use | `windows-overlay-agent.md` |
| RAG, memoria, fuentes, indexacion | `rag-memory-agent.md` |
| Instalador, sidecar, cargo, build | `build-release-agent.md` |
| Test automatizado faltante o flaky | `qa-test-agent.md` |
