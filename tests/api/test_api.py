from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "tests" / "e2e") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "tests" / "e2e"))

from fakes import FakeProvider  # noqa: E402


def build_client(monkeypatch, tmp_path, *, rate_limit="120"):
    monkeypatch.setenv("LOCAL_API_KEY", "test-token")
    monkeypatch.setenv("SEMANTIC_EMBEDDING_PROVIDER", "local_hash")
    monkeypatch.setenv("SEMANTIC_EMBEDDING_MODEL", "local-hash")
    monkeypatch.setenv("CONVERSATIONS_PATH", str(tmp_path / "conversations.sqlite3"))
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("SETTINGS_ENV_PATH", str(tmp_path / ".env"))
    monkeypatch.setenv("API_RATE_LIMIT_PER_MINUTE", rate_limit)

    from src.api import dependencies
    from src.api.app import create_app

    dependencies.api_settings.cache_clear()
    dependencies.local_agent.cache_clear()
    dependencies.agent_service.cache_clear()
    dependencies.memory_service.cache_clear()
    dependencies.settings_service.cache_clear()
    dependencies.event_bus.cache_clear()
    app = create_app()
    client = TestClient(app)
    dependencies.local_agent().provider = FakeProvider(["Hola desde API"])
    return client


def headers():
    return {"x-api-key": "test-token"}


def test_health_endpoint(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    assert client.get("/api/health").json()["ok"] is True


def test_auth_required(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    assert client.get("/api/tools").status_code == 401
    assert client.get("/api/tools", headers=headers()).status_code == 200


def test_chat_basic_mocked(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    response = client.post("/api/chat", headers=headers(), json={"message": "Hola", "use_tools": False})
    assert response.status_code == 200
    body = response.json()
    assert body["message"]["content"] == "Hola desde API"
    assert body["conversation_id"]


def test_chat_opens_google_without_llm_tool_guessing(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)

    from src.api import dependencies
    from src.tools_catalog import local

    opened = []
    monkeypatch.setattr(local.webbrowser, "open", lambda url: opened.append(url) or True)

    response = client.post("/api/chat", headers=headers(), json={"message": "abre google", "use_tools": True})

    assert response.status_code == 200
    body = response.json()
    assert opened == ["https://www.google.com"]
    assert body["message"]["content"] == "Abriendo google."
    assert body["metadata"]["tools_executed"] == ["open_url"]
    assert dependencies.local_agent().provider.requests == []


def test_chat_opens_spotify_as_direct_action(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)

    from src.api import dependencies
    from src.os_integration.apps import InstalledApplication, LaunchResult
    from src.tools_catalog import local

    launched = []

    def fake_launch(query):
        launched.append(query)
        return LaunchResult(
            True,
            query,
            InstalledApplication("spotify", "spotify:", "builtin", "url"),
        )

    monkeypatch.setattr(local.APP_MANAGER, "launch", fake_launch)

    response = client.post("/api/chat", headers=headers(), json={"message": "abre spotify", "use_tools": True})

    assert response.status_code == 200
    body = response.json()
    assert launched == ["spotify"]
    assert body["message"]["content"] == "Abriendo spotify."
    assert body["metadata"]["tools_executed"] == ["open_application"]
    assert dependencies.local_agent().provider.requests == []


def test_chat_searches_youtube_without_llm(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)

    from src.api import dependencies
    from src.tools_catalog import local

    opened = []
    monkeypatch.setattr(local.webbrowser, "open", lambda url: opened.append(url) or True)

    response = client.post(
        "/api/chat",
        headers=headers(),
        json={"message": "busca daft punk en youtube", "use_tools": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert opened == ["https://www.youtube.com/results?search_query=daft+punk"]
    assert body["message"]["content"] == "Buscando daft punk en YouTube."
    assert body["metadata"]["tools_executed"] == ["open_url"]
    assert dependencies.local_agent().provider.requests == []


def test_chat_searches_spotify_without_llm(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)

    from src.tools_catalog import local

    opened = []
    monkeypatch.setattr(local.webbrowser, "open", lambda url: opened.append(url) or True)

    response = client.post(
        "/api/chat",
        headers=headers(),
        json={"message": "buscar nina simone en spotify", "use_tools": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert opened == ["https://open.spotify.com/search/nina%20simone"]
    assert body["message"]["content"] == "Buscando nina simone en Spotify."
    assert body["metadata"]["tools_executed"] == ["open_url"]


def test_chat_volume_and_media_commands_use_keys(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)

    from src.tools_catalog import local

    pressed = []

    class FakePyAutoGui:
        FAILSAFE = True

        @staticmethod
        def press(key):
            pressed.append(key)

    monkeypatch.setattr(local, "pyautogui", FakePyAutoGui)

    volume = client.post("/api/chat", headers=headers(), json={"message": "sube el volumen", "use_tools": True})
    media = client.post("/api/chat", headers=headers(), json={"message": "siguiente", "use_tools": True})

    assert volume.status_code == 200
    assert media.status_code == 200
    assert pressed == ["volumeup", "nexttrack"]
    assert volume.json()["metadata"]["tools_executed"] == ["press_key"]
    assert media.json()["metadata"]["tools_executed"] == ["press_key"]


def test_chat_window_command_uses_semantic_window_tool(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)

    from src.os_integration.models import Rect, WindowInfo, WindowState
    from src.tools_catalog import windows_os

    calls = []

    class FakeWindowManager:
        def maximize_window(self, handle=None, query=None):
            calls.append((handle, query))
            return WindowInfo(
                handle=99,
                title="Spotify",
                process_name="Spotify.exe",
                pid=123,
                rect=Rect(0, 0, 800, 600),
                monitor_index=0,
                state=WindowState.MAXIMIZED,
            )

    class FakeRuntime:
        window_manager = FakeWindowManager()

    monkeypatch.setattr(windows_os, "get_runtime", lambda: FakeRuntime())

    response = client.post("/api/chat", headers=headers(), json={"message": "maximiza spotify", "use_tools": True})

    assert response.status_code == 200
    body = response.json()
    assert calls == [(None, "spotify")]
    assert body["message"]["content"] == "Maximizando spotify."
    assert body["metadata"]["tools_executed"] == ["maximize_window"]


def test_streaming_sse(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    with client.stream("POST", "/api/chat/stream", headers=headers(), json={"message": "Hola", "use_tools": False}) as response:
        text = "".join(response.iter_text())
    assert "message.delta" in text
    assert "message.completed" in text


def test_websocket_connection(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    with client.websocket_connect("/ws/chat?token=test-token") as ws:
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"


def test_tool_list_and_safe_execution(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    tools = client.get("/api/tools", headers=headers()).json()
    assert any(item["name"] == "get_system_info" for item in tools)
    response = client.post("/api/tools/get_system_info/execute", headers=headers(), json={"arguments": {}, "preapproved": True})
    assert response.status_code == 200
    assert "ok" in response.json()


def test_tool_confirmation_required(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    response = client.post("/api/tools/list_directory/execute", headers=headers(), json={"arguments": {"path": str(tmp_path)}})
    assert response.status_code == 200
    assert response.json()["requires_user_action"] in {True, False}


def test_memory_crud(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    created = client.post("/api/memory", headers=headers(), json={"content": "Prefiero respuestas breves"}).json()
    memory_id = created["id"]
    assert client.get("/api/memory", headers=headers()).status_code == 200
    assert client.get("/api/memory/search", headers=headers(), params={"query": "respuestas"}).status_code == 200
    assert client.delete(f"/api/memory/{memory_id}", headers=headers()).json()["deleted"] == memory_id


def test_conversations_crud(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    created = client.post("/api/conversations", headers=headers(), json={"title": "Test"}).json()
    cid = created["id"]
    assert client.get(f"/api/conversations/{cid}", headers=headers()).json()["title"] == "Test"
    assert client.get(f"/api/conversations/{cid}/messages", headers=headers()).json()["total"] == 0
    assert client.delete(f"/api/conversations/{cid}", headers=headers()).json()["deleted"] == cid


def test_settings_masks_secret_and_updates_env(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    body = client.get("/api/settings", headers=headers()).json()
    assert "*" in body["values"]["LMSTUDIO_API_KEY"]
    patched = client.patch(
        "/api/settings",
        headers=headers(),
        json={"values": {"DEFAULT_MODEL": "test-model", "LMSTUDIO_API_KEY": body["values"]["LMSTUDIO_API_KEY"]}},
    ).json()
    assert patched["values"]["DEFAULT_MODEL"] == "test-model"


def test_workflow_run_mock(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    run = client.post("/api/workflows/file_search/run", headers=headers(), json={"input": {"query": "x"}}).json()
    assert run["status"] == "completed"
    assert client.get(f"/api/workflows/runs/{run['run_id']}", headers=headers()).status_code == 200


def test_active_window_metadata(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)

    from src.api.routes import system
    from src.os_integration.models import Rect, WindowInfo, WindowState
    from src.os_integration.security import OSDecision

    class FakeWindowManager:
        def get_active_window(self):
            return WindowInfo(
                handle=123,
                title="Editor",
                process_name="Code.exe",
                pid=456,
                rect=Rect(0, 0, 800, 600),
                monitor_index=0,
                state=WindowState.NORMAL,
            )

        def ensure_window_allowed(self, window, scope):
            return OSDecision(True, "Permitido por test.")

    monkeypatch.setattr(system, "WindowManager", FakeWindowManager)
    response = client.get("/api/system/active-window", headers=headers())
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["allowed"] is True
    assert body["window"]["title"] == "Editor"
    assert body["window"]["sensitive"] is False


def test_active_window_can_exclude_own_overlay(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)

    from src.api.routes import system
    from src.os_integration.models import Rect, WindowInfo, WindowState
    from src.os_integration.security import OSDecision

    overlay = WindowInfo(
        handle=1,
        title="IA Local Agent Overlay",
        process_name="ia-local-agent-desktop.exe",
        pid=10,
        rect=Rect(0, 0, 420, 560),
        monitor_index=0,
        state=WindowState.NORMAL,
    )
    editor = WindowInfo(
        handle=2,
        title="Project - Visual Studio Code",
        process_name="Code.exe",
        pid=20,
        rect=Rect(0, 0, 1200, 800),
        monitor_index=0,
        state=WindowState.NORMAL,
    )

    class FakeWindowManager:
        def get_active_window(self):
            return overlay

        def list_windows(self, limit=25):
            return (overlay, editor)

        def ensure_window_allowed(self, window, scope):
            return OSDecision(True, "Permitido por test.")

    monkeypatch.setattr(system, "WindowManager", FakeWindowManager)
    response = client.get("/api/system/active-window?exclude_own=true", headers=headers())
    assert response.status_code == 200
    body = response.json()
    assert body["window"]["title"] == "Project - Visual Studio Code"
    assert body["window"]["process_name"] == "Code.exe"


def test_cors_restrictive(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    response = client.options(
        "/api/chat",
        headers={
            "Origin": "http://evil.local",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-api-key",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_rate_limit(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path, rate_limit="1")
    assert client.get("/api/tools", headers=headers()).status_code == 200
    assert client.get("/api/tools", headers=headers()).status_code == 429


def test_controlled_errors(monkeypatch, tmp_path):
    client = build_client(monkeypatch, tmp_path)
    response = client.get("/api/tools/not_a_tool", headers=headers())
    assert response.status_code == 404
