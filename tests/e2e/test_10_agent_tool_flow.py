from src.agent import LocalAgent

from fakes import FakeProvider


def test_agent_executes_tool_flow_with_confirmation(monkeypatch, test_settings):
    agent = LocalAgent(settings=test_settings)
    agent.provider = FakeProvider([
        {
            "tool_call": {
                "name": "get_system_info",
                "arguments": "{}",
                "call_id": "call_system",
            }
        },
        "He consultado la información básica del sistema.",
    ])
    monkeypatch.setattr("builtins.input", lambda _: "s")

    agent.submit_user_message("Qué información básica tienes del sistema?")

    messages = agent.conversations.get_messages()
    assert any(message.role == "tool" and message.name == "get_system_info" for message in messages)
    assert messages[-1].content == "He consultado la información básica del sistema."
