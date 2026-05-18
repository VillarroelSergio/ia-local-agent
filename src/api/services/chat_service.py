from __future__ import annotations

import asyncio
import json
from time import monotonic
from typing import Any, AsyncIterator
from uuid import uuid4

from src.agent import LocalAgent
from src.conversations import Message
from src.providers import LLMRequest
from src.api.schemas.chat import AgentMetadata, ChatMessage, ChatRequest, ChatResponse, StreamingChunk, ToolCallEvent
from src.api.schemas.events import EventEnvelope
from src.api.services.event_service import EventBus


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
        tool_events: list[ToolCallEvent] = []
        async for chunk in self.stream_chat(request):
            if chunk.type == "message.completed":
                final = chunk.data
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
            raise RuntimeError("La respuesta del agente no se completo.")
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
            self.agent.conversations.append(Message(
                role="user",
                content=request.message,
                metadata={"context": request.context, "request_id": request_id},
            ))
            await self._publish("message.started", request_id, request.correlation_id, {
                "conversation_id": conversation.id,
            })
            yield self._chunk("message.started", request_id, request.correlation_id, data={"conversation_id": conversation.id})

            try:
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
                payload = {"message": "Error al generar respuesta.", "details": str(error)}
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
        from src.tooling import ToolCall, ToolContext

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
