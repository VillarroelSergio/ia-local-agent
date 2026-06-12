# Security Review Template

## Alcance

Define que flujo, tool, endpoint, overlay, RAG o build se revisa.

## Repositorio

Trabajar en:

```text
https://github.com/VillarroelSergio/ia-local-agent.git
```

## Agentes

- Principal: `qa-test-agent.md`
- Area:
- Apoyo: `backend-api-agent.md` si hay API/tools/auth

## Superficies A Revisar

- Auth local y API key.
- Permisos de tools y confirmaciones.
- Auditoria JSONL.
- Secretos en `.env`, logs, errores y UI.
- RAG: `.ragignore`, scanner de secretos, `safe_source`.
- Overlay: ventanas sensibles, OCR bajo demanda, UAC, password managers.
- Build: exclusion de datos privados.

## Preguntas Clave

- La accion puede leer o escribir datos sensibles?
- Hay confirmacion humana donde toca?
- Hay denegacion explicita para casos peligrosos?
- El usuario ve un error seguro y accionable?
- Se registran auditorias sin filtrar secretos?

## Criterio De Salida

- Riesgos encontrados con archivo/linea o flujo concreto.
- Recomendacion priorizada.
- Pruebas negativas o manuales descritas.
