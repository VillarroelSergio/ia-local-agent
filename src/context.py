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

    def fit(self, system_message, messages):
        budget = max(512, self.max_context_tokens - self.reserved_response_tokens)
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

    def __init__(self, prompt_manager, policy, settings):
        self.prompt_manager = prompt_manager
        self.policy = policy
        self.settings = settings

    def build_messages(self, conversation_messages):
        system_prompt = self.prompt_manager.render_system_prompt(
            provider=self.settings.default_provider,
            model=self.settings.default_model,
        )
        system_message = {
            "role": "system",
            "content": system_prompt,
        }
        provider_messages = [
            message.to_provider_dict()
            for message in conversation_messages
        ]
        return self.policy.fit(system_message, provider_messages)
