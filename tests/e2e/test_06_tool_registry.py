from src.tools import build_tool_registry
from src.tooling import RiskLevel


REQUIRED_TOOLS = {
    "get_system_info",
    "list_directory",
    "read_text_file",
    "search_files",
    "run_powershell",
    "open_application",
    "capture_screenshot",
    "ocr_screen",
    "get_active_window",
    "list_monitors",
}


def test_tool_registry_definitions_are_valid():
    registry = build_tool_registry()
    definitions = registry.definitions()
    names = [definition.name for definition in definitions]

    assert REQUIRED_TOOLS.issubset(set(names))
    assert len(names) == len(set(names))

    for definition in definitions:
        schema = definition.openai_schema()
        assert definition.metadata.name
        assert definition.metadata.description
        assert schema["function"]["parameters"]

    assert registry.require("run_powershell").metadata.requires_confirmation
    assert registry.require("open_application").metadata.risk_level in {
        RiskLevel.USER_CONFIRM,
        RiskLevel.READ_ONLY,
    }
    assert registry.require("capture_screenshot").metadata.risk_level == RiskLevel.READ_ONLY
