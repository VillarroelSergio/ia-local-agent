"""Motor de permisos y politicas de seguridad para tools locales."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import fnmatch

from .models import (
    PermissionDecision,
    PermissionMode,
    RiskLevel,
    ToolContext,
    ToolDefinition,
)


class ToolPermissionPolicy:
    """Politica conservadora por defecto para ejecucion local en Windows."""

    blocked_path_roots = (
        Path("C:/Windows"),
        Path("C:/Windows/System32"),
        Path("C:/Windows/SysWOW64"),
        Path("C:/Windows/WinSxS"),
        Path("C:/Windows/Temp"),
        Path("C:/Windows/Logs"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("C:/ProgramData"),
    )
    blocked_path_fragments = (
        "\\appdata",
        "\\appdata\\local\\google",
        "\\appdata\\local\\microsoft\\edge",
        "\\appdata\\roaming\\mozilla",
        "\\.ssh",
        "\\.aws",
        "\\.azure",
        "\\.docker",
        "\\.kube",
        "\\.gnupg",
        "\\.git-credentials",
        "\\.npmrc",
        "\\.pypirc",
    )
    blocked_file_patterns = (
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
        "id_rsa",
        "id_ed25519",
        "credentials.json",
        "token.json",
        "secrets.*",
    )

    def __init__(
        self,
        *,
        tools_require_confirmation: bool = True,
        allowed_roots: list[Path] | None = None,
        confirm_roots: list[Path] | None = None,
    ):
        self.tools_require_confirmation = tools_require_confirmation
        self.allowed_roots = [root.resolve() for root in allowed_roots or []]
        self.confirm_roots = [root.resolve() for root in confirm_roots or []]

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

        if self._path_requires_confirmation(arguments):
            return PermissionDecision(
                mode=PermissionMode.CONFIRM,
                reason="La ruta solicitada pertenece a una carpeta personal sensible y requiere confirmacion.",
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

            if self._is_blocked_path(resolved):
                return f"Ruta bloqueada por politica de seguridad: {resolved}"

            if self._is_blocked_file(resolved):
                return f"Archivo sensible bloqueado por politica de seguridad: {resolved.name}"

            if any(fragment in lowered for fragment in self.blocked_path_fragments):
                return f"Ruta bloqueada por politica de seguridad: {resolved}"

            allowed_by_root = any(
                self._is_relative_to(resolved, root)
                for root in self.allowed_roots
            )
            allowed_by_confirm_root = any(
                self._is_relative_to(resolved, root)
                for root in self.confirm_roots
            )

            if self.allowed_roots and not allowed_by_root and not allowed_by_confirm_root:
                return f"Ruta fuera de raices permitidas: {resolved}"

        return None

    def _path_requires_confirmation(self, arguments: Any) -> bool:
        data = (
            arguments.model_dump()
            if hasattr(arguments, "model_dump") else arguments
        )

        if not isinstance(data, dict):
            return False

        for key in ("path", "root", "file_path", "directory"):
            value = data.get(key)

            if not isinstance(value, str) or not value.strip():
                continue

            resolved = Path(value).expanduser().resolve()

            if any(self._is_relative_to(resolved, root) for root in self.confirm_roots):
                return True

        return False

    def _is_blocked_path(self, path: Path) -> bool:
        return any(
            self._is_relative_to(path, root.resolve())
            for root in self.blocked_path_roots
        )

    def _is_blocked_file(self, path: Path) -> bool:
        name = path.name.lower()
        return any(
            fnmatch.fnmatch(name, pattern.lower())
            for pattern in self.blocked_file_patterns
        )

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
