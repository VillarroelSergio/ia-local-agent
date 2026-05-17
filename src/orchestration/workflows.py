"""Definiciones conceptuales de workflows agentic reutilizables."""

FILE_SEARCH_WORKFLOW = {
    "name": "file_search",
    "steps": [
        "plan_search_scope",
        "search_files",
        "read_relevant_matches",
        "evaluate_coverage",
        "answer_with_paths",
    ],
    "tools": ["search_files", "read_text_file", "list_directory"],
}

CODE_DEBUG_WORKFLOW = {
    "name": "code_debug",
    "steps": [
        "inspect_project",
        "find_relevant_files",
        "read_code",
        "identify_failure",
        "propose_patch",
        "verify",
    ],
    "tools": ["search_files", "read_text_file", "run_powershell"],
}

WINDOWS_AUTOMATION_WORKFLOW = {
    "name": "windows_automation",
    "steps": [
        "understand_target_app",
        "request_confirmation",
        "execute_ui_action",
        "verify_state",
        "retry_or_report",
    ],
    "tools": ["open_application", "move_mouse", "click_mouse", "hotkey", "type_text"],
}

RAG_TOOL_WORKFLOW = {
    "name": "rag_plus_tools",
    "steps": [
        "retrieve_semantic_context",
        "judge_context_sufficiency",
        "call_filesystem_tools_if_needed",
        "synthesize",
        "store_useful_memory",
    ],
    "tools": ["search_files", "read_text_file"],
}
