"""Fachada compatible del sistema de tools.

El agente historico importa TOOL_SCHEMAS, TOOLS y run_tool desde este modulo.
La implementacion real vive en tooling/ y tools_catalog/ para separar registry,
schemas, permisos, auditoria y ejecucion.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from config import PROJECT_ROOT, get_settings
    from tooling import ToolContext, ToolExecutor, ToolRegistry
    from tooling.audit import JsonlAuditLog
    from tooling.permissions import ToolPermissionPolicy
    from tools_catalog import build_local_tool_definitions, build_windows_os_tool_definitions
    from tools_catalog.rag import build_rag_tool_definitions
except ModuleNotFoundError:
    from src.config import PROJECT_ROOT, get_settings
    from src.tooling import ToolContext, ToolExecutor, ToolRegistry
    from src.tooling.audit import JsonlAuditLog
    from src.tooling.permissions import ToolPermissionPolicy
    from src.tools_catalog import build_local_tool_definitions, build_windows_os_tool_definitions
    from src.tools_catalog.rag import build_rag_tool_definitions


def build_tool_registry():
    """Construye el registry centralizado con las tools locales."""
    registry = ToolRegistry()
    registry.register_many(build_local_tool_definitions())
    registry.register_many(build_windows_os_tool_definitions())
    registry.register_many(build_rag_tool_definitions())
    return registry


def build_tool_executor(registry=None, settings=None):
    """Construye el executor con politica local y auditoria."""
    settings = settings or get_settings()
    allowed_roots = [root.resolve() for root in settings.tool_allowed_roots]
    cwd = Path.cwd().resolve()

    if cwd not in allowed_roots:
        allowed_roots.append(cwd)

    permissions = ToolPermissionPolicy(
        tools_require_confirmation=settings.tools_require_confirmation,
        allowed_roots=allowed_roots,
        confirm_roots=settings.tool_confirm_read_roots,
    )
    audit_log_path = Path(os.getenv("TOOL_AUDIT_LOG_PATH", str(PROJECT_ROOT / "data" / "tool_audit.jsonl")))
    audit_log = JsonlAuditLog(audit_log_path)
    return ToolExecutor(
        registry=registry or build_tool_registry(),
        permissions=permissions,
        audit_log=audit_log,
    )


TOOL_REGISTRY = build_tool_registry()
TOOL_EXECUTOR = build_tool_executor(TOOL_REGISTRY)
TOOL_SCHEMAS = TOOL_REGISTRY.schemas()
TOOLS = {
    name: TOOL_REGISTRY.get(name).handler
    for name in TOOL_REGISTRY.names()
    if TOOL_REGISTRY.get(name) is not None
}


def run_tool(name, arguments=None, *, context=None, preapproved=False):
    """Ejecuta una tool registrada por nombre con argumentos opcionales.

    preapproved=True indica que la capa de UI/CLI ya pidio confirmacion al
    usuario. Esto mantiene el flujo actual de agent.py sin duplicar prompts.
    """
    return TOOL_EXECUTOR.execute_sync(
        name,
        arguments or {},
        context=context or ToolContext(),
        require_preapproved=preapproved,
    )
