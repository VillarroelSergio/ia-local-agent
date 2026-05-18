from pathlib import Path


SENSITIVE_PARTS = [
    "c:\\windows",
    "program files",
    "appdata",
]


def test_safe_configuration_uses_test_paths(test_settings, sandbox):
    assert test_settings.lmstudio_base_url.endswith("/v1")
    assert test_settings.reserved_response_tokens > 0
    assert test_settings.max_context_tokens > 0

    data_paths = [
        test_settings.conversations_path,
        test_settings.chroma_path,
        test_settings.rag_manifest_path,
    ]

    for path in data_paths:
        normalized = str(Path(path)).lower()
        assert str(sandbox).lower() in normalized
        assert not any(part in normalized for part in SENSITIVE_PARTS)
