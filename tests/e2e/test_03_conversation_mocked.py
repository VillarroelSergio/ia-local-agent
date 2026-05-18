from src.agent import LocalAgent

from fakes import FakeProvider


def test_basic_mocked_conversation_is_persisted(test_settings):
    agent = LocalAgent(settings=test_settings)
    agent.provider = FakeProvider(["Hola, soy tu agente local."])

    agent.submit_user_message("Hola")

    messages = agent.conversations.get_messages()
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].content == "Hola"
    assert messages[1].content == "Hola, soy tu agente local."

    reloaded = LocalAgent(settings=test_settings)
    persisted = reloaded.conversations.get_messages()
    assert [message.content for message in persisted] == [
        "Hola",
        "Hola, soy tu agente local.",
    ]
