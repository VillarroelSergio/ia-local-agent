try:
    from os_integration.events import DebounceMiddleware, EventBus, EventPriority, EventType, OSEvent, ThrottleMiddleware
except ModuleNotFoundError:
    from src.os_integration.events import DebounceMiddleware, EventBus, EventPriority, EventType, OSEvent, ThrottleMiddleware

__all__ = ["DebounceMiddleware", "EventBus", "EventPriority", "EventType", "OSEvent", "ThrottleMiddleware"]
