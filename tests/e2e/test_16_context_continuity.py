from src.agent import LocalAgent

from fakes import FakeProvider


def test_regular_turn_preserves_previous_context(test_settings):
    agent = LocalAgent(settings=test_settings)
    provider = FakeProvider([
        "Me llamo contexto.",
        "Recuerdo que te llamas contexto.",
    ])
    agent.provider = provider

    agent.submit_user_message("Mi nombre de prueba es contexto.")
    agent.submit_user_message("Cómo me llamo?")

    second_request = provider.requests[1]
    contents = "\n".join(message["content"] or "" for message in second_request.messages)
    assert "Mi nombre de prueba es contexto." in contents
    assert "Me llamo contexto." in contents
    assert "Cómo me llamo?" in contents


def test_tool_final_prompt_includes_recent_history(monkeypatch, test_settings):
    agent = LocalAgent(settings=test_settings)
    provider = FakeProvider([
        "Tu dato previo era azul.",
        {
            "tool_call": {
                "name": "get_system_info",
                "arguments": "{}",
                "call_id": "call_system",
            }
        },
        "He usado la tool y mantengo que el dato previo era azul.",
    ])
    agent.provider = provider
    monkeypatch.setattr("builtins.input", lambda _: "s")

    agent.submit_user_message("Recuerda para esta prueba que el color es azul.")
    agent.submit_user_message("Consulta el sistema y dime también el color.")

    final_request = provider.requests[-1]
    final_user_message = final_request.messages[-1]["content"]
    assert "Historial reciente" in final_user_message
    assert "color es azul" in final_user_message
    assert "Tu dato previo era azul." in final_user_message
    assert "Resultados de herramientas" in final_user_message
