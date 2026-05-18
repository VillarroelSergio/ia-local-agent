"""Catalogo de tools locales organizadas por dominio."""

from .local import build_local_tool_definitions
from .windows_os import build_windows_os_tool_definitions

__all__ = ["build_local_tool_definitions", "build_windows_os_tool_definitions"]
