import asyncio
from types import SimpleNamespace

from src.computer_use.engine import ComputerUseEngine
from src.computer_use.models import DesktopObservation
from src.os_integration.events import EventPriority, EventType


class CapturingBus:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)
        return True


def _engine_for_publish(bus):
    engine = object.__new__(ComputerUseEngine)
    engine.runtime = SimpleNamespace(event_bus=bus)
    return engine


def test_engine_publish_preserves_only_explicit_safe_payload():
    bus = CapturingBus()
    engine = _engine_for_publish(bus)
    safe_payload = {
        "session_id": "cu_1",
        "iteration": 0,
        "summary": "Editor (code.exe)",
        "changes": {"changed": True},
    }

    asyncio.run(engine._publish(EventType.COMPUTER_USE_OBSERVED, safe_payload))

    event = bus.events[0]
    assert event.payload == safe_payload
    assert event.source == "computer_use"
    assert event.priority is EventPriority.NORMAL


def test_observed_event_contract_excludes_uia_ocr_and_control_values():
    observation = DesktopObservation(
        visible_text="secret copied from OCR",
        screen_summary="Editor (code.exe)",
        metadata={
            "control_value": "private-value",
            "ocr_text": "secret copied from OCR",
        },
    )
    payload = {
        "session_id": "cu_1",
        "iteration": 0,
        "changes": {"changed": True},
        "summary": observation.screen_summary,
    }

    serialized = repr(payload)

    assert observation.visible_text not in serialized
    assert observation.metadata["control_value"] not in serialized
    assert set(payload) == {"session_id", "iteration", "changes", "summary"}


def test_failed_event_uses_high_priority_without_action_arguments():
    bus = CapturingBus()
    engine = _engine_for_publish(bus)
    payload = {"session_id": "cu_1", "error": "policy denied"}

    asyncio.run(
        engine._publish(
            EventType.COMPUTER_USE_FAILED,
            payload,
            priority=EventPriority.HIGH,
        )
    )

    event = bus.events[0]
    assert event.priority is EventPriority.HIGH
    assert event.payload == payload
    assert "args" not in event.payload

