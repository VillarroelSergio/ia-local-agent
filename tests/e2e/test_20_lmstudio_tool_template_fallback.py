from src.agent import LocalAgent
from src.conversations import Message
from src.providers import ProviderError


class ToolTemplateErrorProvider:
    name = "lmstudio"

    def __init__(self):
        self.requests = []

    def stream(self, request):
        self.requests.append(request)
        if request.tools:
            raise ProviderError(
                'Fallo provider lmstudio: Error rendering prompt with jinja template: "No user query found in messages."'
            )
        return iter([Chunk("Respuesta sin tools.")])


class Chunk:
    def __init__(self, content):
        self.choices = [Choice(content)]


class Choice:
    def __init__(self, content):
        self.delta = Delta(content)


class Delta:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


def test_lmstudio_tool_template_error_retries_without_tools(test_settings):
    agent = LocalAgent(settings=test_settings)
    provider = ToolTemplateErrorProvider()
    agent.provider = provider
    agent.conversations.append(Message(role="user", content="centrar ventanas importantes"))

    message, tool_calls = agent.stream_response(use_tools=True)

    assert message == "Respuesta sin tools."
    assert tool_calls == []
    assert provider.requests[0].tools
    assert provider.requests[1].tools is None


class StreamingToolTemplateErrorProvider(ToolTemplateErrorProvider):
    def stream(self, request):
        self.requests.append(request)
        if request.tools:
            return iter([StreamingErrorChunk()])
        return iter([Chunk("Respuesta sin tools.")])


class StreamingErrorChunk:
    @property
    def choices(self):
        raise ProviderError(
            'Fallo provider lmstudio: Error rendering prompt with jinja template: "No user query found in messages."'
        )


class HistoryTemplateErrorProvider:
    name = "lmstudio"

    def __init__(self):
        self.requests = []

    def stream(self, request):
        self.requests.append(request)
        if len(self.requests) == 1:
            raise ProviderError(
                'Fallo provider lmstudio: Error rendering prompt with jinja template: "No user query found in messages."'
            )
        return iter([Chunk("Respuesta con contexto minimo.")])


def test_lmstudio_streaming_tool_template_error_retries_without_tools(test_settings):
    agent = LocalAgent(settings=test_settings)
    provider = StreamingToolTemplateErrorProvider()
    agent.provider = provider
    agent.conversations.append(Message(role="user", content="busca este archivo HerejiaHorus.rar"))

    message, tool_calls = agent.stream_response(use_tools=True)

    assert message == "Respuesta sin tools."
    assert tool_calls == []
    assert provider.requests[0].tools
    assert provider.requests[1].tools is None
    assert [message["role"] for message in provider.requests[1].messages] == ["user"]


def test_lmstudio_plain_fallback_collapses_to_single_user_message(test_settings):
    agent = LocalAgent(settings=test_settings)
    messages = [
        {"role": "system", "content": "Sistema con instrucciones."},
        {"role": "assistant", "content": "Respuesta previa."},
        {"role": "user", "content": "busca este archivo HerejiaHorus.rar"},
    ]

    fallback = agent.build_lmstudio_plain_fallback_messages(messages)

    assert len(fallback) == 1
    assert fallback[0]["role"] == "user"
    assert "HerejiaHorus.rar" in fallback[0]["content"]


def test_lmstudio_template_error_without_tools_retries_with_minimal_context(test_settings):
    agent = LocalAgent(settings=test_settings)
    agent.native_tools_enabled = False
    provider = HistoryTemplateErrorProvider()
    agent.provider = provider
    agent.conversations.append(Message(role="user", content="como me llamo"))

    message, tool_calls = agent.stream_response(use_tools=True)

    assert message == "Respuesta con contexto minimo."
    assert tool_calls == []
    assert len(provider.requests) == 2
    assert provider.requests[0].tools is None
    assert provider.requests[1].tools is None
    assert [item["role"] for item in provider.requests[1].messages] == ["user"]
