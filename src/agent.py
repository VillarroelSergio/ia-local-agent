"""Orquestador principal del agente IA local.

El agente coordina configuracion, provider LLM, prompts, contexto,
conversaciones, memoria y tools. La CLI vive al final del archivo por
compatibilidad, pero el nucleo ya puede reutilizarse desde una UI o API local.
"""

import json
import sys
from datetime import datetime
from time import monotonic
from uuid import uuid4

try:
    from config import get_settings
    from context import ApproxTokenCounter, ContextBuilder, SlidingWindowPolicy
    from conversations import ConversationManager, ConversationStore, Message
    from prompts import PromptManager
    from providers import LLMRequest, ProviderError, build_provider_registry
    from rag import LocalRagService
    from semantic_memory import SemanticMemoryManager
    from tools import TOOL_REGISTRY, TOOL_SCHEMAS, run_tool
except ModuleNotFoundError:
    from src.config import get_settings
    from src.context import ApproxTokenCounter, ContextBuilder, SlidingWindowPolicy
    from src.conversations import ConversationManager, ConversationStore, Message
    from src.prompts import PromptManager
    from src.providers import LLMRequest, ProviderError, build_provider_registry
    from src.rag import LocalRagService
    from src.semantic_memory import SemanticMemoryManager
    from src.tools import TOOL_REGISTRY, TOOL_SCHEMAS, run_tool


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
            embedding_base_url=self.settings.lmstudio_base_url,
            embedding_api_key=self.settings.lmstudio_api_key,
            long_term_enabled=self.settings.long_term_memory_enabled,
        )
        self.rag = LocalRagService(self.settings)
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
        request_id = uuid4().hex
        turn_started_at = monotonic()
        context_started_at = monotonic()
        fallback_used = False
        fallback_reason = None

        if lmstudio_compat is None:
            lmstudio_compat = self.provider.name == "lmstudio"

        extra_reserved_tokens = 0
        selected_tools = TOOL_SCHEMAS if use_tools else None
        if use_tools:
            query = self.context_builder.get_last_user_input(
                self.conversations.get_messages()
            )
            selected_tools = self.select_tool_schemas(query)
            tools_payload = json.dumps(selected_tools, ensure_ascii=False)
            extra_reserved_tokens = (len(tools_payload) // 4) + 256

        messages = self.context_builder.build_messages(
            self.conversations.get_messages(),
            lmstudio_compat=lmstudio_compat,
            extra_reserved_tokens=extra_reserved_tokens,
        )
        context_ms = self._duration_ms(context_started_at)
        request = LLMRequest(
            model=self.settings.default_model,
            messages=messages,
            temperature=self.settings.temperature,
            tools=selected_tools,
            tool_choice="auto" if use_tools else None,
            stream=True,
        )

        print("\nIA: ", end="", flush=True)

        try:
            provider_started_at = monotonic()
            stream = self.provider.stream(request)
            provider_open_ms = self._duration_ms(provider_started_at)
            assistant_message, tool_calls, stream_metrics = self.consume_provider_stream(stream)
        except Exception as error:
            if not (use_tools and self.is_lmstudio_tool_template_error(error)):
                raise
            fallback_used = True
            fallback_reason = "lmstudio_tool_template_error"
            print("\nAviso: LM Studio no pudo renderizar tools con el template del modelo. Reintentando sin tools.")
            fallback_messages = self.build_lmstudio_plain_fallback_messages(messages)
            request = LLMRequest(
                model=self.settings.default_model,
                messages=fallback_messages,
                temperature=self.settings.temperature,
                tools=None,
                tool_choice=None,
                stream=True,
                metadata={"tool_fallback": "lmstudio_template_error"},
            )
            provider_started_at = monotonic()
            stream = self.provider.stream(request)
            provider_open_ms = self._duration_ms(provider_started_at)
            assistant_message, tool_calls, stream_metrics = self.consume_provider_stream(stream)

        normalized_tool_calls = []

        for index, tool_call in tool_calls.items():
            if not tool_call["id"]:
                tool_call["id"] = f"call_{index}"

            normalized_tool_calls.append(tool_call)

        print()
        self.log_turn_timing({
            "request_id": request_id,
            "conversation_id": self.conversations.get_active().id,
            "provider": self.provider.name,
            "model": request.model,
            "context_ms": context_ms,
            "provider_open_ms": provider_open_ms,
            "first_content_ms": stream_metrics["first_content_ms"],
            "stream_ms": stream_metrics["stream_ms"],
            "total_ms": self._duration_ms(turn_started_at),
            "message_chars": len(assistant_message or ""),
            "approx_output_tokens": max(0, len(assistant_message or "") // 4),
            "tool_calls": len(normalized_tool_calls),
            "tools_sent": bool(selected_tools),
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
        })
        return assistant_message, normalized_tool_calls

    def consume_provider_stream(self, stream):
        assistant_message = ""
        tool_calls = {}
        stream_started_at = monotonic()
        first_content_ms = None

        for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                if first_content_ms is None:
                    first_content_ms = self._duration_ms(stream_started_at)
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

        return assistant_message, tool_calls, {
            "first_content_ms": first_content_ms,
            "stream_ms": self._duration_ms(stream_started_at),
        }

    def log_turn_timing(self, payload):
        """Registra latencias del turno en data/agent_timing.jsonl."""
        if not self.settings.agent_timing_log_enabled:
            return

        event = {
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "event_type": "agent.turn_timing",
            **payload,
        }
        log_path = self.settings.project_root / "data" / "agent_timing.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            pass

        if self.settings.agent_timing_log_console:
            first = payload.get("first_content_ms")
            first_text = f"{first}ms" if first is not None else "n/a"
            print(
                "[timing] "
                f"total={payload['total_ms']}ms "
                f"context={payload['context_ms']}ms "
                f"provider_open={payload['provider_open_ms']}ms "
                f"first_token={first_text} "
                f"stream={payload['stream_ms']}ms "
                f"chars={payload['message_chars']} "
                f"tools_sent={payload['tools_sent']} "
                f"fallback={payload['fallback_used']}"
            )

    @staticmethod
    def _duration_ms(started_at):
        return int((monotonic() - started_at) * 1000)

    def is_lmstudio_tool_template_error(self, error):
        text = str(error).lower()
        return (
            self.provider.name == "lmstudio"
            and "jinja" in text
            and "no user query found" in text
        )

    def build_lmstudio_plain_fallback_messages(self, messages):
        user_messages = [
            (message.get("content") or "").strip()
            for message in messages
            if message.get("role") == "user" and (message.get("content") or "").strip()
        ]
        latest_user = user_messages[-1] if user_messages else "Continua la conversacion."
        return [{
            "role": "user",
            "content": (
                "Responde de forma breve y util. El soporte nativo de tools del modelo local fallo, "
                "asi que no ejecutes acciones: explica que puedes hacerlo cuando el modelo soporte tools "
                "o cuando usemos el modo textual de tools.\n\n"
                f"Peticion del usuario:\n{latest_user}"
            ),
        }]

    def select_tool_schemas(self, query):
        """Reduce schemas enviados al modelo segun la intencion del turno."""
        normalized = (query or "").lower()

        groups = {
            "windows": {
                "get_active_window",
                "list_windows",
                "focus_window",
                "move_window",
                "resize_window",
                "maximize_window",
                "minimize_window",
                "close_window",
                "tile_windows_layout",
                "list_monitors",
            },
            "vision": {
                "take_screenshot",
                "take_region_screenshot",
                "take_window_screenshot",
                "ocr_active_window",
                "ocr_region",
                "summarize_screen",
                "capture_screenshot",
                "ocr_screen",
                "get_active_window",
            },
            "system": {"get_system_info", "get_running_processes", "run_powershell"},
            "files": {"list_directory", "read_text_file", "search_files", "search_local_knowledge"},
            "apps": {"open_application", "open_notepad", "open_calculator", "list_installed_applications"},
            "clipboard": {"get_clipboard", "set_clipboard"},
        }
        intent_keywords = [
            (groups["windows"], ("ventana", "ventanas", "monitor", "monitores", "centrar", "mueve", "mover", "pon ", "organiza", "maximiza", "minimiza", "cierra", "cerrar", "spotify", "chrome", "vscode", "vs code")),
            (groups["vision"], ("pantalla", "captura", "screenshot", "ocr", "visible", "resume la ventana", "lee el texto", "imagen")),
            (groups["system"], ("sistema", "cpu", "ram", "memoria", "procesos", "powershell", "servicios")),
            (groups["files"], ("archivo", "archivos", "carpeta", "directorio", "readme", "docs", "documentacion", "busca en")),
            (groups["apps"], ("abre", "abrir", "aplicacion", "app", "notepad", "calculadora", "explorer")),
            (groups["clipboard"], ("portapapeles", "clipboard", "copiar", "pegar")),
        ]

        selected_names = set()
        for names, keywords in intent_keywords:
            if any(keyword in normalized for keyword in keywords):
                selected_names.update(names)

        if not selected_names:
            selected_names.update({
                "get_system_info",
                "get_running_processes",
                "get_active_window",
                "list_windows",
                "take_screenshot",
                "summarize_screen",
                "search_local_knowledge",
                "open_application",
            })

        definitions = [
            definition
            for definition in TOOL_REGISTRY.definitions()
            if definition.name in selected_names
        ]
        return [definition.openai_schema() for definition in definitions]

    def stream_final_response_after_tools(self, original_user_input, tool_results):
        """Pide respuesta final con historial reciente compatible con LM Studio."""
        system_prompt = self.prompt_manager.render_system_prompt(
            provider=self.settings.default_provider,
            model=self.settings.default_model,
            memory_context=self.semantic_memory.format_explicit_for_prompt(),
            semantic_context=self.semantic_memory.format_for_prompt(original_user_input),
        )
        tool_context = json.dumps(tool_results, indent=2, ensure_ascii=False)
        recent_context = self.format_recent_conversation_for_prompt(
            exclude_current_tool_trace=True,
        )
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    "Responde al usuario usando el historial reciente y estos resultados de herramientas.\n\n"
                    f"Historial reciente:\n{recent_context}\n\n"
                    f"Peticion original del usuario:\n{original_user_input}\n\n"
                    f"Resultados de herramientas:\n{tool_context}"
                ),
            },
        ]
        request = LLMRequest(
            model=self.settings.default_model,
            messages=messages,
            temperature=self.settings.temperature,
            tools=None,
            tool_choice=None,
            stream=True,
        )
        stream = self.provider.stream(request)
        assistant_message = ""

        print("\nIA: ", end="", flush=True)

        for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                print(delta.content, end="", flush=True)
                assistant_message += delta.content

        print()
        return assistant_message

    def format_recent_conversation_for_prompt(
        self,
        *,
        limit=12,
        exclude_current_tool_trace=False,
    ):
        """Convierte historial reciente a texto estable para prompts compactos."""
        messages = self.conversations.get_messages()

        if exclude_current_tool_trace:
            messages = self.strip_trailing_tool_trace(messages)

        selected = messages[-limit:]
        lines = []

        for message in selected:
            label = f"tool:{message.name or 'tool'}" if message.role == "tool" else message.role
            content = (message.content or "").strip()

            if not content and message.tool_calls:
                content = "[tool call solicitada]"

            if not content:
                continue

            lines.append(f"{label}: {content}")

        return "\n".join(lines) if lines else "No hay historial previo relevante."

    def strip_trailing_tool_trace(self, messages):
        """Elimina assistant/tool del turno actual para no duplicar resultados."""
        trimmed = list(messages)

        while trimmed and trimmed[-1].role in {"tool", "assistant"}:
            last = trimmed[-1]

            if last.role == "assistant" and not last.tool_calls:
                break

            trimmed.pop()

        return trimmed

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

    def handle_rag_command(self, user_input):
        """Gestiona comandos manuales de RAG documental."""
        if user_input.startswith("/rag_index "):
            raw = user_input.removeprefix("/rag_index ").strip()
            project_id = "default"
            path = raw

            if " --project " in raw:
                path, _, project_id = raw.partition(" --project ")
                path = path.strip()
                project_id = project_id.strip() or "default"

            result = self.rag.index_path(path, project_id=project_id)
            print("\nRAG index:", json.dumps(result, indent=2, ensure_ascii=False))
            return True

        if user_input.startswith("/rag_search "):
            query = user_input.removeprefix("/rag_search ").strip()
            result = self.rag.search(query)
            print("\nRAG:")
            print(self.rag.format_context(result, max_chars=6000))
            print("\nTrace:", json.dumps(result.trace, indent=2, ensure_ascii=False))
            return True

        if user_input == "/rag_stats":
            print("\nRAG:", json.dumps(self.rag.stats(), indent=2, ensure_ascii=False))
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
        original_user_input = self.context_builder.get_last_user_input(
            self.conversations.get_messages()
        )
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

        tool_results = []

        for tool_call in tool_calls:
            result = self.run_confirmed_tool_call(tool_call)
            print("\nTool:", result)
            tool_results.append({
                "tool": tool_call["function"]["name"],
                "result": result,
            })

            self.conversations.append(Message(
                role="tool",
                content=json.dumps(result, ensure_ascii=False),
                tool_call_id=tool_call["id"],
                name=tool_call["function"]["name"],
            ))

        final_message = self.stream_final_response_after_tools(
            original_user_input,
            tool_results,
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
    print(f"Provider: {agent.settings.default_provider} | Modelo: {agent.settings.default_model}")
    print()
    print("Puedes pedirme tareas como:")
    print("- Ventanas: \"cierra Spotify\", \"maximiza VS Code\", \"pon Chrome a la derecha\", \"organiza mis ventanas\".")
    print("- Pantalla/OCR: \"resume la ventana actual\", \"lee el texto visible\", \"haz una captura de pantalla\".")
    print("- Sistema: \"que procesos consumen mas memoria\", \"dame informacion del sistema\".")
    print("- Archivos/RAG: \"busca en mis docs como ejecutar el agente\", \"lee README.md\", \"lista esta carpeta\".")
    print("- Memoria: \"recuerda que prefiero respuestas breves\", o usa /remember, /memories, /memory_search.")
    print()
    print("Comandos directos: /tool nombre {json}, /rag_index ruta [--project nombre], /rag_search pregunta.")

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

        if agent.handle_rag_command(user_input):
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
