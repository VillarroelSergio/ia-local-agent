"""Fakes reutilizables para pruebas e2e."""

from __future__ import annotations

from types import SimpleNamespace


class FakeProvider:
    """Provider OpenAI-compatible en memoria para turnos e2e."""

    name = "fake"

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.requests = []

    def stream(self, request):
        self.requests.append(request)
        response = self.responses.pop(0) if self.responses else "OK"

        if isinstance(response, dict) and response.get("tool_call"):
            yield fake_tool_call_chunk(**response["tool_call"])
            return

        yield fake_content_chunk(str(response))

    def list_models(self):
        return [{"id": "fake-model"}]

    def healthcheck(self):
        return True


def fake_content_chunk(content):
    delta = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def fake_tool_call_chunk(name, arguments="{}", call_id="call_fake"):
    function = SimpleNamespace(name=name, arguments=arguments)
    tool_call = SimpleNamespace(index=0, id=call_id, function=function)
    delta = SimpleNamespace(content=None, tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])
