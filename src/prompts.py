"""Gestion centralizada de prompts del agente."""


DEFAULT_SYSTEM_TEMPLATE = """
Eres un asistente IA local integrado en Windows.
Ayudas al usuario con tareas diarias y desarrollo.
Puedes pedir herramientas cuando sean utiles, pero el usuario siempre debe
confirmar antes de ejecutarlas.

Proveedor activo: {provider}
Modelo activo: {model}

Memoria persistente relevante del usuario:
{memory_context}

Memoria semantica recuperada para este turno:
{semantic_context}
""".strip()


class PromptManager:
    """Renderiza system prompts versionables y preparados para contexto."""

    def __init__(self, template=None, version="v1"):
        self.template = template or DEFAULT_SYSTEM_TEMPLATE
        self.version = version

    def render_system_prompt(
        self,
        *,
        provider,
        model,
        memory_context=None,
        semantic_context=None,
        extra_context=None,
    ):
        context = {
            "provider": provider,
            "model": model,
            "memory_context": memory_context or "No hay memoria persistente guardada todavia.",
            "semantic_context": semantic_context or "No hay memoria semantica relevante.",
        }

        if extra_context:
            context.update(extra_context)

        return self.template.format(**context)
