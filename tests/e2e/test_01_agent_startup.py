from src.agent import LocalAgent


def test_agent_starts_with_isolated_settings(test_settings):
    agent = LocalAgent(settings=test_settings)

    assert agent.settings.default_model == "fake-model"
    assert agent.provider is not None
    assert agent.conversations.current_length() == 0
