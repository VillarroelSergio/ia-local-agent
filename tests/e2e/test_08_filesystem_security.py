from pathlib import Path

import pytest

from src.tools import build_tool_executor, build_tool_registry


BLOCKED_PATHS = [
    r"C:\Windows",
    r"C:\Windows\System32",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\ProgramData",
    str(Path.home() / "AppData"),
    str(Path.home() / ".ssh"),
    str(Path.home() / ".aws"),
    str(Path.home() / ".kube"),
    str(Path.home() / ".docker"),
]


@pytest.fixture()
def isolated_executor(test_settings):
    return build_tool_executor(build_tool_registry(), settings=test_settings)


@pytest.mark.parametrize("tool_name,args", [
    ("read_text_file", {"path": r"C:\Windows\win.ini", "max_chars": 10}),
    ("list_directory", {"path": r"C:\Windows", "limit": 5}),
    ("search_files", {"path": r"C:\Windows", "pattern": "*.ini", "limit": 5}),
])
def test_blocked_sensitive_filesystem_paths(isolated_executor, tool_name, args):
    result = isolated_executor.execute_sync(
        tool_name,
        args,
        require_preapproved=True,
    )
    assert "error" in result
    assert result["error_type"] == "permission_denied"


@pytest.mark.parametrize("path", BLOCKED_PATHS)
def test_blocked_path_list_directory(isolated_executor, path):
    result = isolated_executor.execute_sync(
        "list_directory",
        {"path": path, "limit": 3},
        require_preapproved=True,
    )
    assert "error" in result
    assert result["error_type"] == "permission_denied"


def test_allowed_sandbox_read_list_search(isolated_executor, sandbox):
    file_path = sandbox / "note.txt"
    file_path.write_text("contenido seguro", encoding="utf-8")

    read_result = isolated_executor.execute_sync(
        "read_text_file",
        {"path": str(file_path), "max_chars": 100},
        require_preapproved=True,
    )
    list_result = isolated_executor.execute_sync(
        "list_directory",
        {"path": str(sandbox), "limit": 10},
        require_preapproved=True,
    )
    search_result = isolated_executor.execute_sync(
        "search_files",
        {"path": str(sandbox), "pattern": "*.txt", "limit": 10},
        require_preapproved=True,
    )

    assert read_result["content"] == "contenido seguro"
    assert list_result["count"] >= 1
    assert str(file_path) in search_result["matches"]
