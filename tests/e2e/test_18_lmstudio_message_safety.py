from src.providers import LMStudioProvider


def test_lmstudio_provider_preserves_user_message():
    provider = LMStudioProvider(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        default_model="local",
    )

    messages = provider.prepare_messages([
        {"role": "system", "content": "Eres util."},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1"}]},
        {"role": "tool", "name": "close_window", "content": '{"closed_requested": true}'},
    ])

    assert any(message["role"] == "user" for message in messages)
    assert messages[-1]["role"] == "user"


def test_lmstudio_provider_drops_trailing_assistant():
    provider = LMStudioProvider(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        default_model="local",
    )

    messages = provider.prepare_messages([
        {"role": "user", "content": "Cierra Spotify"},
        {"role": "assistant", "content": "Hecho."},
    ])

    assert messages == [{"role": "user", "content": "Cierra Spotify"}]
