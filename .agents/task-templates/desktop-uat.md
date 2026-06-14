# Desktop UAT Execution Template

## Objetivo

Ejecutar en la aplicacion Windows un plan de casos de uso mediante prompts y
comprobar resultados visibles, confirmaciones, efectos y seguridad.

## Agentes

- Gate: `testing-agent.md`
- Diseno de casos: `user-acceptance-test-agent.md`
- Ejecucion: `desktop-uat-agent.md`
- Diagnostico: `bug-agent.md`
- Automatizacion de regresion: `qa-test-agent.md`

## Entorno

- Fecha:
- Rama:
- Commit:
- Tipo de app: Tauri dev / build / instalador
- Backend:
- LM Studio:
- Modelo:
- Windows:
- Escala DPI:
- Monitores:
- Aplicacion objetivo:
- Ruta de evidencias:

## Preflight

- [ ] Working tree y commit registrados.
- [ ] API `/api/health` responde.
- [ ] LM Studio responde o el caso espera su ausencia.
- [ ] App desktop abierta y conectada.
- [ ] Datos de prueba sinteticos preparados.
- [ ] No hay ventanas sensibles abiertas.
- [ ] Se conoce como restaurar el estado tras cada caso.

## Casos

| ID | Prompt exacto | Aplicacion/contexto | Confirmacion esperada | Resultado visible esperado | Estado |
| --- | --- | --- | --- | --- | --- |
| UAT-01 |  |  |  |  | NOT_RUN |

## Registro Por Caso

```text
Caso:
Inicio/fin:
Prompt exacto:
Estado inicial:
Acciones observadas:
Confirmacion mostrada:
Decision de confirmacion:
Resultado visible:
Verificacion posterior:
Timeline/eventos:
Evidencia:
Resultado: PASS / FAIL / BLOCKED / NEEDS_INFO / NOT_RUN
Notas:
```

## Seguridad

| ID | Superficie | Accion solicitada | Bloqueo esperado | Resultado |
| --- | --- | --- | --- | --- |
| SEC-01 | Ventana sensible simulada | Lectura/accion | Sin titulo, OCR ni contenido | NOT_RUN |

## Resumen

```text
PASS:
FAIL:
BLOCKED:
NEEDS_INFO:
NOT_RUN:
Decision del gate:
Fallos enviados a:
Regresiones automatizadas creadas:
Riesgos residuales:
```

