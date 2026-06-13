from src.computer_use.intents import detect_computer_use_intent


def test_uat_prompts_route_to_computer_use():
    cases = {
        "Analiza la ventana activa sin hacer OCR.": ("observe_window", False),
        "Extrae el texto visible de la ventana activa.": ("observe_window", False),
        "Busca el boton Guardar, pero no lo pulses.": ("find_ui_control", False),
        "Organiza mis ventanas.": ("tile_windows_layout", True),
        "Lee todo el contenido de la ventana activa.": ("observe_window", False),
    }

    for prompt, expected in cases.items():
        intent = detect_computer_use_intent(prompt)
        assert intent is not None
        assert (intent.tool_name, intent.requires_confirmation) == expected


def test_generic_web_search_is_not_claimed():
    assert detect_computer_use_intent("Busca Daft Punk en YouTube") is None
