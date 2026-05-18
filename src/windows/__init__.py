"""Domain-oriented Windows Task Runtime facade.

This package is the public architecture for semantic Windows capabilities.
The implementation currently delegates to ``os_integration`` services to keep
backwards compatibility with the existing tool runtime.
"""

from __future__ import annotations

try:
    from os_integration import WindowsIntegrationRuntime
except ModuleNotFoundError:
    from src.os_integration import WindowsIntegrationRuntime


WindowsTaskManager = WindowsIntegrationRuntime

__all__ = ["WindowsIntegrationRuntime", "WindowsTaskManager"]
