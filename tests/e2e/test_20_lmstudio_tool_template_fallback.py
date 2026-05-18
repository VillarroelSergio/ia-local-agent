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
