from __future__ import annotations

import asyncio
import json
from time import monotonic
from typing import Any, AsyncIterator
from uuid import uuid4

from src.agent import LocalAgent
from src.computer_use.intents import detect_computer_use_intent
from src.conversations import Message
from src.providers import LLMRequest
from src.simple_actions import SimpleAction, detect_simple_action
from src.api.schemas.chat import AgentMetadata, ChatMessage, ChatRequest, ChatResponse, StreamingChunk, ToolCallEvent
from src.api.schemas.events import EventEnvelope
from src.api.services.event_service import EventBus
from src.tooling import ToolCall, ToolContext


class AgentService:
    """Async API adapter around LocalAgent without duplicating core logic."""

    def __init__(self, agent: LocalAgent, event_bus: EventBus):
        self.agent = agent
        self.event_bus = event_bus
        self._lock = asyncio.Lock()
        self._cancelled: set[str] = set()

    def cancel(self, request_id: str):
        self._cancelled.add(request_id)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        final = None
        error_payload = None
        tool_events: list[ToolCallEvent] = []
        async for chunk in self.stream_chat(request):
            if chunk.type == "message.completed":
                final = chunk.data
            if chunk.type == "error":
                error_payload = chunk.data
            if chunk.type.startswith("tool."):
                name = chunk.data.get("name")
                if name:
                    tool_events.append(ToolCallEvent(
                        id=chunk.data.get("id", ""),
                        name=name,
                        arguments=chunk.data.get("arguments", {}),
                        risk_level=chunk.data.get("risk_level"),
                        status=chunk.type.removeprefix("tool."),
                    ))
        if final is None:
            details = (error_payload or {}).get("details") or (error_payload or {}).get("message")
            raise RuntimeError(details or "La respuesta del agente no se completo.")
        return ChatResponse(
            conversation_id=final["conversation_id"],
            message=ChatMessage(**final["message"]),
            tool_calls=tool_events,
            metadata=AgentMetadata(**final["metadata"]),
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamingChunk]:
        request_id = uuid4().hex
        started_at = monotonic()
        text = ""
        final_text = ""
        tools_executed: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []

        async with self._lock:
            conversation = self._select_conversation(request.conversation_id)
            history_length = self.agent.conversations.current_length()
            user_content = self._message_with_context(request.message, request.context)
            self.agent.conversations.append(Message(
                role="user",
                content=user_content,
                metadata={"context": request.context, "request_id": request_id},
            ))
            await self._publish("message.started", request_id, request.correlation_id, {
                "conversation_id": conversation.id,
            })
            yield self._chunk("message.started", request_id, request.correlation_id, data={"conversation_id": conversation.id})

            try:
                simple_action = (
                    detect_computer_use_intent(request.message)
                    or detect_simple_action(request.message)
                ) if request.use_tools else None
                if simple_action:
                    async for chunk in self._execute_simple_action(
                        simple_action,
                        conversation.id,
                        request_id,
                        request.correlation_id,
                    ):
                        if chunk.type == "message.delta" and chunk.delta:
                            text += chunk.delta
                            final_text += chunk.delta
                        if chunk.type == "tool.completed":
                            tools_executed.append(chunk.data.get("name", ""))
                        yield chunk

                    self.agent.index_new_conversation_messages(history_length)
                    message = self.agent.conversations.get_messages()[-1]
                    metadata = AgentMetadata(
                        provider=request.provider or self.agent.provider.name,
                        model=request.model or self.agent.settings.default_model,
                        duration_ms=int((monotonic() - started_at) * 1000),
                        approximate_tokens=max(1, len((text or "").split())),
                        tools_executed=tools_executed,
                        request_id=request_id,
                        correlation_id=request.correlation_id,
                    )
                    payload = {
                        "conversation_id": conversation.id,
                        "message": self._message_to_dict(message),
                        "metadata": metadata.model_dump(),
                    }
                    await self._publish("message.completed", request_id, request.correlation_id, payload)
                    yield self._chunk("message.completed", request_id, request.correlation_id, data=payload)
                    return

                async for chunk in self._provider_stream(request, request_id):
                    if request_id in self._cancelled:
                        raise asyncio.CancelledError()
                    if chunk.type == "message.delta" and chunk.delta:
                        text += chunk.delta
                    if chunk.type == "tool.requested":
                        tool_calls.append(chunk.data["tool_call"])
                    yield chunk

                if tool_calls:
                    self.agent.conversations.append(Message(
                        role="assistant",
                        content=text or None,
                        tool_calls=tool_calls,
                    ))
                    async for event in self._execute_tool_calls(tool_calls, conversation.id, request_id, request.correlation_id):
                        if event.type == "tool.completed":
                            tools_executed.append(event.data.get("name", ""))
                        if event.type in {"tool.completed", "tool.failed", "tool.confirmation_required"}:
                            tool_results.append({
                                "tool": event.data.get("name", ""),
                                "result": event.data.get("result")
                                if event.type == "tool.completed"
                                else event.data.get("error"),
                            })
                        yield event
                    async for chunk in self._final_response_after_tools(
                        request,
                        request_id,
                        conversation.id,
                        tool_results,
                    ):
                        if chunk.type == "message.delta" and chunk.delta:
                            final_text += chunk.delta
                            text += chunk.delta
                        yield chunk
                    self.agent.conversations.append(Message(role="assistant", content=final_text))
                else:
                    self.agent.conversations.append(Message(role="assistant", content=text))

                self.agent.index_new_conversation_messages(history_length)
                message = self.agent.conversations.get_messages()[-1]
                metadata = AgentMetadata(
                    provider=request.provider or self.agent.provider.name,
                    model=request.model or self.agent.settings.default_model,
                    duration_ms=int((monotonic() - started_at) * 1000),
                    approximate_tokens=max(1, len((text or "").split())),
                    tools_executed=tools_executed,
                    request_id=request_id,
                    correlation_id=request.correlation_id,
                )
                payload = {
                    "conversation_id": conversation.id,
                    "message": self._message_to_dict(message),
                    "metadata": metadata.model_dump(),
                }
                await self._publish("message.completed", request_id, request.correlation_id, payload)
                yield self._chunk("message.completed", request_id, request.correlation_id, data=payload)
            except asyncio.CancelledError:
                self.agent.conversations.remove_messages_after(history_length)
                yield self._chunk("error", request_id, request.correlation_id, data={"message": "Generacion cancelada."})
            except Exception as error:
                removed_ids = self.agent.conversations.remove_messages_after(history_length)
                self.agent.semantic_memory.delete_conversation_messages(removed_ids)
                payload = {
                    "message": "Error al generar respuesta.",
                    "details": str(error),
                    "provider": self.agent.provider.name,
                    "model": request.model or self.agent.settings.default_model,
                }
                await self._publish("error", request_id, request.correlation_id, payload)
                yield self._chunk("error", request_id, request.correlation_id, data=payload)

    async def _provider_stream(self, request: ChatRequest, request_id: str) -> AsyncIterator[StreamingChunk]:
        selected_tools = self.agent.select_tool_schemas(request.message) if request.use_tools else None
        if not self.agent.native_tools_enabled:
            selected_tools = None
        messages = self.agent.context_builder.build_messages(
            self.agent.conversations.get_messages(),
            lmstudio_compat=self.agent.provider.name == "lmstudio",
            extra_reserved_tokens=256 if selected_tools else 0,
        )
        if self.agent.provider.name == "lmstudio" and self.agent.settings.lmstudio_minimal_chat:
            messages = self.agent.build_lmstudio_plain_fallback_messages(messages)
        llm_request = LLMRequest(
            model=request.model or self.agent.settings.default_model,
            messages=messages,
            temperature=self.agent.settings.temperature,
            tools=selected_tools,
            tool_choice="auto" if selected_tools else None,
            stream=True,
        )
        stream = await asyncio.to_thread(self.agent.provider.stream, llm_request)
        tool_calls: dict[int, dict[str, Any]] = {}
        for raw in stream:
            delta = raw.choices[0].delta
            if getattr(delta, "content", None):
                chunk = self._chunk("message.delta", request_id, request.correlation_id, delta=delta.content)
                await self._publish(chunk.type, request_id, request.correlation_id, chunk.model_dump())
                yield chunk
            if getattr(delta, "tool_calls", None):
                for call in delta.tool_calls:
                    current = tool_calls.setdefault(call.index, {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    })
                    if call.id:
                        current["id"] += call.id
                    if call.function:
                        if call.function.name:
                            current["function"]["name"] += call.function.name
                        if call.function.arguments:
                            current["function"]["arguments"] += call.function.arguments
        for index, call in tool_calls.items():
            if not call["id"]:
                call["id"] = f"call_{index}"
            args = self._parse_arguments(call)
            payload = {"id": call["id"], "name": call["function"]["name"], "arguments": args, "tool_call": call}
            yield self._chunk("tool.requested", request_id, request.correlation_id, data=payload)

    async def _execute_tool_calls(self, tool_calls, conversation_id, request_id, correlation_id):
        for call in tool_calls:
            name = call["function"]["name"]
            args = self._parse_arguments(call)
            started = self._chunk("tool.started", request_id, correlation_id, data={"id": call["id"], "name": name, "arguments": args})
            await self._publish(started.type, request_id, correlation_id, started.data)
            yield started
            result = await self.agent.tool_executor.execute(
                ToolCall(id=call["id"], name=name, arguments=args, conversation_id=conversation_id),
                ToolContext(conversation_id=conversation_id, settings=self.agent.settings),
                require_preapproved=False,
            )
            event_type = "tool.confirmation_required" if result.requires_user_action else ("tool.completed" if result.ok else "tool.failed")
            self.agent.conversations.append(Message(
                role="tool",
                content=json.dumps(result.to_message_content(), ensure_ascii=False),
                tool_call_id=call["id"],
                name=name,
            ))
            data = result.model_dump(mode="json")
            data.update({"id": call["id"], "name": name})
            yield self._chunk(event_type, request_id, correlation_id, data=data)

    async def _execute_simple_action(self, action: SimpleAction, conversation_id: str, request_id: str, correlation_id: str | None):
        call = ToolCall(name=action.tool_name, arguments=action.arguments, conversation_id=conversation_id)
        requested_data = {
            "id": call.id,
            "name": action.tool_name,
            "arguments": action.arguments,
            "tool_call": {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": action.tool_name,
                    "arguments": json.dumps(action.arguments, ensure_ascii=False),
                },
            },
        }
        yield self._chunk("tool.requested", request_id, correlation_id, data=requested_data)
        yield self._chunk("tool.started", request_id, correlation_id, data={
            "id": call.id,
            "name": action.tool_name,
            "arguments": action.arguments,
        })
        result = await self.agent.tool_executor.execute(
            call,
            ToolContext(conversation_id=conversation_id, settings=self.agent.settings),
            require_preapproved=not getattr(action, "requires_confirmation", False),
        )
        self.agent.conversations.append(Message(
            role="tool",
            content=json.dumps(result.to_message_content(), ensure_ascii=False),
            tool_call_id=call.id,
            name=action.tool_name,
        ))
        data = result.model_dump(mode="json")
        data.update({"id": call.id, "name": action.tool_name})
        event_type = "tool.confirmation_required" if result.requires_user_action else ("tool.completed" if result.ok else "tool.failed")
        yield self._chunk(event_type, request_id, correlation_id, data=data)

        message = self._format_simple_action_response(action, result.to_message_content(), result.requires_user_action)
        self.agent.conversations.append(Message(role="assistant", content=message))
        yield self._chunk("message.delta", request_id, correlation_id, delta=message)

    @staticmethod
    def _format_simple_action_response(action: SimpleAction, result: Any, requires_user_action: bool = False):
        if requires_user_action:
            return "Esta accion requiere tu confirmacion antes de organizar las ventanas."
        if isinstance(result, dict) and result.get("error"):
            return f"No he podido hacerlo: {result['error']}"
        if action.tool_name == "observe_window" and isinstance(result, dict):
            if result.get("blocked_by_policy"):
                return "No puedo leer esa ventana porque esta bloqueada por la politica de seguridad."
            text = str(result.get("visible_text") or "").strip()
            summary = str(result.get("screen_summary") or "Ventana activa observada.").strip()
            if text:
                return f"{summary}\n\nTexto accesible:\n{text[:4000]}"
            return f"{summary}\n\nNo se encontro texto accesible mediante UI Automation. No se ejecuto OCR."
        if action.tool_name == "find_ui_control" and isinstance(result, dict):
            control = result.get("control")
            if control:
                return f"Control encontrado: {control.get('name')} ({control.get('control_type')}). No se ha pulsado."
            return "No se encontro ese control mediante UI Automation. No se ha realizado ninguna accion."
        if action.tool_name == "computer_use" and isinstance(result, dict):
            status = result.get("status")
            session_id = result.get("id")
            if status == "waiting_confirmation":
                pending = (result.get("state") or {}).get("pending_confirmation") or {}
                description = pending.get("description") or "La siguiente accion modifica la ventana."
                return (
                    f"Sesion Computer Use {session_id} preparada. {description} "
                    "Necesito tu confirmacion para continuar."
                )
            if status == "completed":
                return f"Sesion Computer Use {session_id} completada y verificada."
            error = result.get("error")
            if status in {"failed", "aborted", "cancelled"}:
                return f"La sesion Computer Use {session_id} termino como {status}: {error or 'sin detalle adicional'}."
            return f"Sesion Computer Use {session_id} en estado {status or 'desconocido'}."
        return action.user_message

    async def _final_response_after_tools(self, request: ChatRequest, request_id: str, conversation_id: str, tool_results: list[dict[str, Any]]):
        system_prompt = self.agent.prompt_manager.render_system_prompt(
            provider=request.provider or self.agent.settings.default_provider,
            model=request.model or self.agent.settings.default_model,
            memory_context=self.agent.semantic_memory.format_explicit_for_prompt(),
            semantic_context=self.agent.semantic_memory.format_for_prompt(request.message),
        )
        recent_context = self.agent.format_recent_conversation_for_prompt(
            exclude_current_tool_trace=True,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Responde al usuario usando el historial reciente y estos resultados de herramientas.\n\n"
                    f"Historial reciente:\n{recent_context}\n\n"
                    f"Peticion original del usuario:\n{request.message}\n\n"
                    f"Resultados de herramientas:\n{json.dumps(tool_results, indent=2, ensure_ascii=False)}"
                ),
            },
        ]
        llm_request = LLMRequest(
            model=request.model or self.agent.settings.default_model,
            messages=messages,
            temperature=self.agent.settings.temperature,
            tools=None,
            tool_choice=None,
            stream=True,
        )
        stream = await asyncio.to_thread(self.agent.provider.stream, llm_request)
        for raw in stream:
            delta = raw.choices[0].delta
            if getattr(delta, "content", None):
                chunk = self._chunk("message.delta", request_id, request.correlation_id, delta=delta.content)
                await self._publish(chunk.type, request_id, request.correlation_id, chunk.model_dump())
                yield chunk

    def _select_conversation(self, conversation_id: str | None):
        if conversation_id:
            return self.agent.conversations.set_active(conversation_id)
        return self.agent.conversations.create_conversation()

    @staticmethod
    def _parse_arguments(call):
        raw = call["function"].get("arguments") or "{}"
        try:
            value = json.loads(raw)
            return value if isinstance(value, dict) else {"_raw_arguments": raw}
        except json.JSONDecodeError:
            return {"_raw_arguments": raw}

    @staticmethod
    def _message_to_dict(message: Message) -> dict[str, Any]:
        return {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
            "metadata": message.metadata,
            "tool_calls": message.tool_calls,
            "tool_call_id": message.tool_call_id,
            "name": message.name,
        }

    def _chunk(self, type_: str, request_id: str, correlation_id: str | None, *, delta=None, data=None):
        return StreamingChunk(type=type_, delta=delta, data=data or {}, request_id=request_id, correlation_id=correlation_id)

    async def _publish(self, type_: str, request_id: str, correlation_id: str | None, data: dict[str, Any]):
        await self.event_bus.publish(EventEnvelope(type=type_, data=data, request_id=request_id, correlation_id=correlation_id))

    @staticmethod
    def _message_with_context(message: str, context: dict[str, Any] | None) -> str:
        if not context:
            return message
        context_text = json.dumps(context, ensure_ascii=False, indent=2)
        if len(context_text) > 2500:
            context_text = f"{context_text[:2500]}\n... contexto truncado ..."
        return f"{message}\n\n[Contexto local seguro]\n{context_text}"
