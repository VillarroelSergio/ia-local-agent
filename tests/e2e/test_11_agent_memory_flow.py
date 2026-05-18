from src.agent import LocalAgent

from fakes import FakeProvider


def test_agent_memory_command_and_retrieval(test_settings):
    agent = LocalAgent(settings=test_settings)
    assert agent.handle_memory_command(
        "/remember Prefiero respuestas breves en español"
    )

    memory_context = agent.semantic_memory.format_for_prompt(
        "Cómo prefiero que me respondas?"
    )
    assert "respuestas breves" in memory_context

    agent.provider = FakeProvider(["Prefieres respuestas breves en español."])
    agent.submit_user_message("Cómo prefiero que me respondas?")

    assert agent.conversations.get_messages()[-1].content == (
        "Prefieres respuestas breves en español."
    )
