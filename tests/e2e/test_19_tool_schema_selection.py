import json

from src.agent import LocalAgent


def tool_names(schemas):
    return {schema["function"]["name"] for schema in schemas}


def test_window_request_sends_compact_window_toolset(test_settings):
    agent = LocalAgent(settings=test_settings)

    schemas = agent.select_tool_schemas("centrar ventanas importantes en sus monitores")
    names = tool_names(schemas)

    assert "list_windows" in names
    assert "tile_windows_layout" in names
    assert "run_powershell" not in names
    assert "search_local_knowledge" not in names
    assert len(json.dumps(schemas, ensure_ascii=False)) // 4 < 1800


def test_screen_summary_request_sends_vision_toolset(test_settings):
    agent = LocalAgent(settings=test_settings)

    schemas = agent.select_tool_schemas("resume la ventana actual")
    names = tool_names(schemas)

    assert "summarize_screen" in names
    assert "ocr_active_window" in names
    assert "move_mouse" not in names
