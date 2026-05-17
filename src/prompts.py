"""Gestion centralizada de prompts del agente."""

try:
    from memory import format_memories_for_prompt
except ModuleNotFoundError:
    from src.memory import format_memories_for_prompt


DEFAULT_SYSTEM_TEMPLATE = """
Eres un asistente IA local integrado en Windows.
Ayudas al usuario con tareas diarias y desarrollo.
Puedes pedir herramientas cuando sean utiles, pero el usuario siempre debe
confirmar antes de ejecutarlas.

Proveedor activo: {provider}
Modelo activo: {model}

Memoria persistente relevante del usuario:
{memory_context}
""".strip()


class PromptManager:
    """Renderiza system prompts versionables y preparados para contexto."""

    def __init__(self, template=None, version="v1"):
        self.template = template or DEFAULT_SYSTEM_TEMPLATE
        self.version = version

    def render_system_prompt(self, *, provider, model, memory_context=None, extra_context=None):
        context = {
            "provider": provider,
            "model": model,
            "memory_context": memory_context or format_memories_for_prompt(),
        }

        if extra_context:
            context.update(extra_context)

        return self.template.format(**context)
