"""Capability registry for Computer Use."""

SEMANTIC_CAPABILITIES: tuple[str, ...] = (
    "focus_window",
    "summarize_active_window",
    "open_project_workspace",
    "capture_and_analyze_screen",
    "extract_visible_text",
    "find_ui_control",
    "click_ui_control",
    "fill_form",
    "organize_windows",
    "automate_task",
)

HIGH_RISK_CAPABILITIES: frozenset[str] = frozenset({
    "click_ui_control",
    "fill_form",
    "organize_windows",
    "automate_task",
    "capture_and_analyze_screen",
})


def is_high_risk(capability: str) -> bool:
    return capability in HIGH_RISK_CAPABILITIES
