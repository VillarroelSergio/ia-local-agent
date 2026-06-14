# Decision Trace Template

Plantilla para mostrar el enrutamiento de agentes y la trazabilidad de decisiones tras recibir un prompt.

## Prompt

```text
<prompt del usuario>
```

## Clasificacion

- Tipo de tarea:
- Areas afectadas:
- Nivel de riesgo: bajo / medio / alto
- Requiere cambios de codigo: si / no
- Requiere pruebas: si / no
- Requiere documentacion: si / no

## Ruta De Agentes

| Rol | Agente | Motivo |
| --- | --- | --- |
| Principal | `<agente>` | `<por que lidera>` |
| Apoyo | `<agente>` | `<por que ayuda>` |
| QA | `qa-test-agent.md` | `<riesgos y pruebas>` |

## Decisiones Iniciales

| Decision | Motivo | Impacto |
| --- | --- | --- |
| `<decision>` | `<razon>` | `<archivos/flujo afectado>` |

## Alternativas Descartadas

| Alternativa | Motivo de descarte |
| --- | --- |
| `<alternativa>` | `<razon>` |

## Evidencia Consultada

- Archivos:
- Docs:
- Tests:
- Comandos:

## Cambios De Rumbo

| Momento | Cambio | Motivo |
| --- | --- | --- |
| `<durante exploracion/implementacion/pruebas>` | `<cambio>` | `<razon>` |

## Validacion Prevista

```powershell
# comandos o comprobaciones esperadas
```

## Resultado

- Archivos cambiados:
- Pruebas ejecutadas:
- Pruebas no ejecutadas:
- Riesgos residuales:
- Siguiente paso recomendado:
