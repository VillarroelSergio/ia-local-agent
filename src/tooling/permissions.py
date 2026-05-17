"""Motor de permisos y politicas de seguridad para tools locales."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    PermissionDecision,
    PermissionMode,
    RiskLevel,
    ToolContext,
    ToolDefinition,
)


class ToolPermissionPolicy:
    """Politica conservadora por defecto para ejecucion local en Windows."""

    blocked_path_fragments = (
        "\\windows",
        "\\program files",
        "\\program files (x86)",
        "\\appdata\\roaming\\microsoft\\credentials",
        "\\.ssh",
    )

    def __init__(
        self,
        *,
        tools_require_confirmation: bool = True,
        allowed_roots: list[Path] | None = None,
    ):
        self.tools_require_confirmation = tools_require_confirmation
        self.allowed_roots = [root.resolve() for root in allowed_roots or []]

    def evaluate(
        self,
        definition: ToolDefinition,
        arguments: Any,
        context: ToolContext,
    ) -> PermissionDecision:
        metadata = definition.metadata
        risk_level = metadata.risk_level

        path_error = self._validate_path_arguments(arguments)

        if path_error:
            return PermissionDecision(
                mode=PermissionMode.DENY,
                reason=path_error,
                risk_level=risk_level,
            )

        if risk_level in {RiskLevel.DESTRUCTIVE, RiskLevel.ADMIN}:
            return PermissionDecision(
                mode=PermissionMode.DENY,
                reason="La tool esta clasificada como peligrosa o administrativa.",
                risk_level=risk_level,
            )

        if metadata.requires_confirmation and self.tools_require_confirmation:
            return PermissionDecision(
                mode=PermissionMode.CONFIRM,
                reason="La politica requiere confirmacion del usuario.",
                risk_level=risk_level,
            )

        return PermissionDecision(
            mode=PermissionMode.ALLOW,
            reason="Permitido por politica.",
            risk_level=risk_level,
        )

    def _validate_path_arguments(self, arguments: Any) -> str | None:
        data = (
            arguments.model_dump()
            if hasattr(arguments, "model_dump") else arguments
        )

        if not isinstance(data, dict):
            return None

        for key in ("path", "root", "file_path", "directory"):
            value = data.get(key)

            if not isinstance(value, str) or not value.strip():
                continue

            resolved = Path(value).expanduser().resolve()
            lowered = str(resolved).lower()

            if any(fragment in lowered for fragment in self.blocked_path_fragments):
                return f"Ruta bloqueada por politica de seguridad: {resolved}"

            if self.allowed_roots and not any(
                self._is_relative_to(resolved, root)
                for root in self.allowed_roots
            ):
                return f"Ruta fuera de raices permitidas: {resolved}"

        return None

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
