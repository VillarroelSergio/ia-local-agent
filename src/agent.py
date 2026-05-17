"""Orquestador principal del agente IA local.

El agente coordina configuracion, provider LLM, prompts, contexto,
conversaciones, memoria y tools. La CLI vive al final del archivo por
compatibilidad, pero el nucleo ya puede reutilizarse desde una UI o API local.
"""

import json
import sys

try:
    from config import get_settings
    from context import ApproxTokenCounter, ContextBuilder, SlidingWindowPolicy
    from conversations import ConversationManager, ConversationStore, Message
    from prompts import PromptManager
    from providers import LLMRequest, ProviderError, build_provider_registry
    from semantic_memory import SemanticMemoryManager
    from tools import TOOL_SCHEMAS, run_tool
except ModuleNotFoundError:
    from src.config import get_settings
    from src.context import ApproxTokenCounter, ContextBuilder, SlidingWindowPolicy
    from src.conversations import ConversationManager, ConversationStore, Message
    from src.prompts import PromptManager
    from src.providers import LLMRequest, ProviderError, build_provider_registry
    from src.semantic_memory import SemanticMemoryManager
    from src.tools import TOOL_SCHEMAS, run_tool


class LocalAgent:
    """Servicio de agente reutilizable por CLI, UI desktop o API."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.providers = build_provider_registry(self.settings)
        self.provider = self.providers.get(self.settings.default_provider)
        self.prompt_manager = PromptManager()
        self.semantic_memory = SemanticMemoryManager(
            path=self.settings.chroma_path,
            enabled=self.settings.semantic_memory_enabled,
            max_results=self.settings.semantic_memory_results,
            embedding_provider=self.settings.semantic_embedding_provider,
            embedding_model=self.settings.semantic_embedding_model,
            long_term_enabled=self.settings.long_term_memory_enabled,
        )
        self.conversations = ConversationManager(
            ConversationStore(self.settings.conversations_path)
        )
        self.context_builder = ContextBuilder(
            prompt_manager=self.prompt_manager,
            policy=SlidingWindowPolicy(
                token_counter=ApproxTokenCounter(),
                max_context_tokens=self.settings.max_context_tokens,
                reserved_response_tokens=self.settings.reserved_response_tokens,
            ),
            settings=self.settings,
            semantic_memory=self.semantic_memory,
        )

    def stream_response(self, use_tools=True, lmstudio_compat=None):
        """Solicita una respuesta al modelo y la imprime en streaming."""
        if lmstudio_compat is None:
            lmstudio_compat = self.provider.name == "lmstudio"

        extra_reserved_tokens = 0
        if use_tools:
            tools_payload = json.dumps(TOOL_SCHEMAS, ensure_ascii=False)
            extra_reserved_tokens = (len(tools_payload) // 4) + 256

        messages = self.context_builder.build_messages(
            self.conversations.get_messages(),
            lmstudio_compat=lmstudio_compat,
            extra_reserved_tokens=extra_reserved_tokens,
        )
        request = LLMRequest(
            model=self.settings.default_model,
            messages=messages,
            temperature=self.settings.temperature,
            tools=TOOL_SCHEMAS if use_tools else None,
            tool_choice="auto" if use_tools else None,
            stream=True,
        )

        stream = self.provider.stream(request)

        assistant_message = ""
        tool_calls = {}

        print("\nIA: ", end="", flush=True)

        for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                print(delta.content, end="", flush=True)
                assistant_message += delta.content

            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    index = tool_call.index

                    if index not in tool_calls:
                        tool_calls[index] = {
                            "id": "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": "",
                            },
                        }

                    if tool_call.id:
                        tool_calls[index]["id"] += tool_call.id

                    if tool_call.function:
                        if tool_call.function.name:
                            tool_calls[index]["function"]["name"] += tool_call.function.name

                        if tool_call.function.arguments:
                            tool_calls[index]["function"]["arguments"] += tool_call.function.arguments

        normalized_tool_calls = []

        for index, tool_call in tool_calls.items():
            if not tool_call["id"]:
                tool_call["id"] = f"call_{index}"

            normalized_tool_calls.append(tool_call)

        print()
        return assistant_message, normalized_tool_calls

    def parse_tool_arguments(self, tool_call):
        """Convierte los argumentos JSON de una tool call en un diccionario."""
        raw_arguments = tool_call["function"].get("arguments") or "{}"

        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            return {
                "_error": "No se pudieron leer los argumentos JSON de la tool.",
                "_raw_arguments": raw_arguments,
            }

        if not isinstance(arguments, dict):
            return {
                "_error": "Los argumentos de la tool deben ser un objeto JSON.",
                "_raw_arguments": raw_arguments,
            }

        return arguments

    def confirm_tool(self, tool_name, arguments):
        """Pide confirmacion antes de ejecutar una tool solicitada."""
        if not self.settings.tools_require_confirmation:
            return True

        print(f"\nEl modelo quiere ejecutar '{tool_name}' con argumentos:")
        print(json.dumps(arguments, indent=2, ensure_ascii=False))
        answer = input("Confirmar? (s/n): ")
        return answer.strip().lower() in ["s", "si", "y", "yes"]

    def run_confirmed_tool_call(self, tool_call):
        """Valida, confirma y ejecuta una tool call del modelo."""
        tool_name = tool_call["function"]["name"]
        arguments = self.parse_tool_arguments(tool_call)

        if "_error" in arguments:
            return arguments

        if not self.confirm_tool(tool_name, arguments):
            return "Tool cancelada por el usuario."

        return run_tool(tool_name, arguments, preapproved=True)

    def handle_memory_command(self, user_input):
        """Gestiona comandos manuales de memoria."""
        if user_input.startswith("/remember "):
            content = user_input.removeprefix("/remember ").strip()
            memory = self.semantic_memory.remember(content)
            print("\nMemoria:", memory)
            return True

        if user_input == "/memories":
            memories = self.semantic_memory.list_memories()
            print("\nMemorias:")

            if not memories:
                print("No hay memoria persistente guardada todavia.")
                return True

            for memory in memories:
                print(
                    f"- [{memory.get('id')}] "
                    f"({memory.get('category')}, importancia {memory.get('importance')}) "
                    f"{memory.get('content')}"
                )

            return True

        if user_input.startswith("/memory_search "):
            query = user_input.removeprefix("/memory_search ").strip()
            results = self.semantic_memory.search(query)
            print("\nMemoria semantica:")

            if not results:
                print("No hay resultados relevantes.")
                return True

            for result in results:
                source = result.metadata.get("type", "semantic")
                distance = (
                    f"{result.distance:.4f}"
                    if result.distance is not None else "n/a"
                )
                print(f"- [{source}:{result.id} d={distance}] {result.content}")

            return True

        if user_input == "/memory_stats":
            print("\nMemoria:", self.semantic_memory.memory_stats())
            return True

        if user_input == "/memory_rebuild":
            result = self.rebuild_semantic_memory()
            print("\nMemoria:", result)
            return True

        if user_input.startswith("/forget "):
            memory_id = user_input.removeprefix("/forget ").strip()
            result = self.semantic_memory.forget(memory_id)
            print("\nMemoria:", result)
            return True

        return False

    def handle_tool_command(self, user_input):
        """Ejecuta tools manuales desde la CLI."""
        if not user_input.startswith("/tool "):
            return False

        tool_request = user_input.removeprefix("/tool ").strip()
        tool_name, _, raw_arguments = tool_request.partition(" ")

        try:
            arguments = json.loads(raw_arguments) if raw_arguments else {}
        except json.JSONDecodeError as error:
            print("\nTool: JSON invalido en los argumentos:", error)
            return True

        result = run_tool(tool_name.lower(), arguments, preapproved=True)
        print("\nTool:", result)
        return True

    def chat_once(self):
        """Procesa una interaccion completa de chat."""
        assistant_message, tool_calls = self.stream_response(use_tools=True)

        if not tool_calls:
            self.conversations.append(Message(
                role="assistant",
                content=assistant_message,
            ))
            return

        self.conversations.append(Message(
            role="assistant",
            content=assistant_message or None,
            tool_calls=tool_calls,
        ))

        for tool_call in tool_calls:
            result = self.run_confirmed_tool_call(tool_call)
            print("\nTool:", result)

            self.conversations.append(Message(
                role="tool",
                content=json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call["id"],
                name=tool_call["function"]["name"],
            ))

        final_message, _ = self.stream_response(
            use_tools=False,
            lmstudio_compat=True,
        )

        self.conversations.append(Message(
            role="assistant",
            content=final_message,
        ))

    def submit_user_message(self, content):
        """Anade un mensaje del usuario y ejecuta un turno del agente."""
        history_length = self.conversations.current_length()
        self.conversations.append(Message(role="user", content=content))

        try:
            self.chat_once()
            self.index_new_conversation_messages(history_length)
        except ProviderError:
            removed_ids = self.conversations.remove_messages_after(history_length)
            self.semantic_memory.delete_conversation_messages(removed_ids)
            raise
        except Exception:
            removed_ids = self.conversations.remove_messages_after(history_length)
            self.semantic_memory.delete_conversation_messages(removed_ids)
            raise

    def index_new_conversation_messages(self, history_length):
        """Indexa en Chroma los mensajes nuevos de un turno completado."""
        messages = self.conversations.get_messages()

        for message in messages[history_length:]:
            self.semantic_memory.add_conversation_message(message)

    def rebuild_semantic_memory(self):
        """Reindexa en Chroma todos los mensajes persistidos en SQLite."""
        indexed = 0

        for conversation in self.conversations.conversations.values():
            for message in conversation.messages:
                before = indexed
                self.semantic_memory.add_conversation_message(message)

                if message.role in {"user", "assistant"} and message.content:
                    indexed = before + 1

        return {
            "indexed_messages": indexed,
            **self.semantic_memory.memory_stats(),
        }


def configure_console_output():
    """Evita errores Unicode al imprimir respuestas del modelo en Windows."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def main():
    """Bucle principal de consola del agente."""
    configure_console_output()
    agent = LocalAgent()

    print("Agente IA local iniciado. Escribe 'salir' para terminar.")
    print("Tools manuales: /tool notepad, /tool calc, /tool sistema")
    print("Memoria: /remember texto, /memories, /memory_search texto, /memory_stats, /memory_rebuild, /forget id")
    print(f"Provider: {agent.settings.default_provider} | Modelo: {agent.settings.default_model}")

    while True:
        try:
            user_input = input("\nTu: ").strip()
        except EOFError:
            break

        if user_input.lower() == "salir":
            break

        if not user_input:
            continue

        if agent.handle_memory_command(user_input):
            continue

        if agent.handle_tool_command(user_input):
            continue

        try:
            agent.submit_user_message(user_input)
        except Exception as error:
            print("\nError al conectar con LM Studio:", error)
            print("Comprueba que el server esta activo y que hay un modelo cargado.")
            continue


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAgente detenido.")
