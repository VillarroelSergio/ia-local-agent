"""Construccion y recorte del contexto enviado al modelo."""


class ApproxTokenCounter:
    """Contador aproximado de tokens.

    Es suficiente para la primera arquitectura. Mas adelante puede sustituirse
    por tiktoken o tokenizadores especificos por modelo.
    """

    def count_text(self, text):
        if not text:
            return 0

        return max(1, len(text) // 4)

    def count_message(self, message):
        content = message.get("content") if isinstance(message, dict) else message.content
        return self.count_text(content) + 8


class SlidingWindowPolicy:
    """Mantiene el system prompt y los mensajes recientes dentro del presupuesto."""

    def __init__(self, token_counter, max_context_tokens, reserved_response_tokens):
        self.token_counter = token_counter
        self.max_context_tokens = max_context_tokens
        self.reserved_response_tokens = reserved_response_tokens

    def fit(self, system_message, messages, extra_reserved_tokens=0):
        budget = max(
            512,
            self.max_context_tokens
            - self.reserved_response_tokens
            - extra_reserved_tokens,
        )
        selected = []
        used = self.token_counter.count_message(system_message)

        for message in reversed(messages):
            message_tokens = self.token_counter.count_message(message)

            if used + message_tokens > budget:
                break

            selected.append(message)
            used += message_tokens

        selected.reverse()
        return [system_message, *selected]


class ContextBuilder:
    """Compone el contexto final con prompt, historial y futuras inyecciones."""

    def __init__(self, prompt_manager, policy, settings, semantic_memory=None):
        self.prompt_manager = prompt_manager
        self.policy = policy
        self.settings = settings
        self.semantic_memory = semantic_memory

    def build_messages(
        self,
        conversation_messages,
        lmstudio_compat=False,
        extra_reserved_tokens=0,
    ):
        query = self.get_last_user_input(conversation_messages)
        semantic_context = (
            self.semantic_memory.format_for_prompt(query)
            if self.semantic_memory is not None else None
        )
        memory_context = (
            self.semantic_memory.format_explicit_for_prompt()
            if self.semantic_memory is not None else None
        )
        system_prompt = self.prompt_manager.render_system_prompt(
            provider=self.settings.default_provider,
            model=self.settings.default_model,
            memory_context=memory_context,
            semantic_context=semantic_context,
        )
        system_message = {
            "role": "system",
            "content": system_prompt,
        }
        provider_messages = [
            message.to_provider_dict()
            for message in conversation_messages
        ]

        if lmstudio_compat:
            provider_messages = self.to_lmstudio_compatible_messages(provider_messages)

        return self.policy.fit(
            system_message,
            provider_messages,
            extra_reserved_tokens=extra_reserved_tokens,
        )

    def get_last_user_input(self, conversation_messages):
        for message in reversed(conversation_messages):
            if message.role == "user" and message.content:
                return message.content

        return ""

    def to_lmstudio_compatible_messages(self, messages):
        """Evita roles tool en plantillas Jinja de LM Studio poco tolerantes."""
        compatible_messages = []

        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if role == "tool":
                tool_name = message.get("name") or "tool"
                compatible_messages.append({
                    "role": "user",
                    "content": (
                        f"Resultado de la herramienta {tool_name}:\n"
                        f"{content or ''}\n\n"
                        "Usa este resultado para responder al usuario."
                    ),
                })
                continue

            clean_message = {
                "role": role,
                "content": content or "",
            }

            compatible_messages.append(clean_message)

        return compatible_messages
