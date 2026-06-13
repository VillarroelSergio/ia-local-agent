from datetime import datetime, timedelta

from src.computer_use.models import ComputerUseSession, ComputerUseStatus, DesktopObservation
from src.computer_use.sessions import ComputerUseSessionStore


def test_store_returns_none_for_unknown_session(tmp_path):
    store = ComputerUseSessionStore(tmp_path / "sessions.sqlite3")

    assert store.get("missing") is None


def test_store_round_trips_all_mutable_session_fields(tmp_path):
    store = ComputerUseSessionStore(tmp_path / "sessions.sqlite3")
    completed_at = datetime.now()
    session = ComputerUseSession(
        goal="leer el editor",
        status=ComputerUseStatus.COMPLETED,
        state={"iteration": 2, "nested": {"ok": True}},
        completed_at=completed_at,
        error=None,
    )
    session.record_observation(DesktopObservation(visible_text="resultado"))
    session.record_action({"ok": True, "items": ("a", "b")})

    store.save(session)
    loaded = store.get(session.id)

    assert loaded is not None
    assert loaded.to_dict() == session.to_dict()


def test_save_updates_existing_session_instead_of_duplicating_it(tmp_path):
    store = ComputerUseSessionStore(tmp_path / "sessions.sqlite3")
    session = ComputerUseSession(goal="objetivo inicial")
    store.save(session)

    session.goal = "objetivo actualizado"
    session.status = ComputerUseStatus.FAILED
    session.error = "controlled failure"
    session.record_action({"ok": False})
    store.save(session)

    loaded = store.get(session.id)
    assert loaded is not None
    assert loaded.goal == "objetivo actualizado"
    assert loaded.status is ComputerUseStatus.FAILED
    assert loaded.error == "controlled failure"
    assert len(store.list_recent(limit=10)) == 1


def test_list_recent_orders_by_updated_at_and_honors_limit(tmp_path):
    store = ComputerUseSessionStore(tmp_path / "sessions.sqlite3")
    now = datetime.now()
    sessions = [
        ComputerUseSession(goal="old", updated_at=now - timedelta(minutes=2)),
        ComputerUseSession(goal="new", updated_at=now),
        ComputerUseSession(goal="middle", updated_at=now - timedelta(minutes=1)),
    ]
    for session in sessions:
        store.save(session)

    recent = store.list_recent(limit=2)

    assert [session.goal for session in recent] == ["new", "middle"]

