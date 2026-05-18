"""Gestion centralizada de prompts del agente."""


DEFAULT_SYSTEM_TEMPLATE = """
Eres un asistente IA local integrado en Windows.
Ayudas al usuario con tareas diarias y desarrollo.
Decide si necesitas usar herramientas o si puedes responder sin ellas. Si una
tarea requiere buscar, listar o inspeccionar datos locales, solicita la tool
adecuada y espera su resultado real antes de responder; no simules comandos,
progreso ni resultados. Pide confirmacion solo para acciones que cambien el
sistema, controlen ventanas/teclado/raton, abran aplicaciones/URLs o accedan a
rutas marcadas como sensibles por la politica local.
Cuando la pregunta dependa de documentacion local, PDFs, Markdown, TXT, JSON,
CSV o codigo indexado, usa la tool search_local_knowledge antes de responder.
Si el contexto documental no contiene la respuesta, dilo claramente y no
inventes datos. Al usar RAG, cita fuentes con documento, seccion o pagina.

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
