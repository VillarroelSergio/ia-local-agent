from src.simple_actions import detect_simple_action


def test_compound_open_request_is_not_parsed_as_an_application_name():
    prompt = (
        "Abre Notepad con un documento nuevo y vacio. Cuando este listo, "
        "analiza su ventana sin usar OCR."
    )

    assert detect_simple_action(prompt) is None
