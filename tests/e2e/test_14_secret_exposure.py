import pytest

from src.tools import build_tool_executor, build_tool_registry


SECRET_FILES = [
    ".env",
    "token.json",
    "credentials.json",
    "id_rsa",
]


@pytest.fixture()
def isolated_executor(test_settings):
    return build_tool_executor(build_tool_registry(), settings=test_settings)


def test_agent_can_read_safe_file_but_not_secret_files(isolated_executor, sandbox):
    (sandbox / "test.txt").write_text("safe", encoding="utf-8")

    for name in SECRET_FILES:
        (sandbox / name).write_text("secret", encoding="utf-8")

    safe_result = isolated_executor.execute_sync(
        "read_text_file",
        {"path": str(sandbox / "test.txt"), "max_chars": 100},
        require_preapproved=True,
    )
    assert safe_result["content"] == "safe"

    for name in SECRET_FILES:
        result = isolated_executor.execute_sync(
            "read_text_file",
            {"path": str(sandbox / name), "max_chars": 100},
            require_preapproved=True,
        )
        assert result["error_type"] == "permission_denied"
