"""Registro dinamico de tools con busqueda por metadata."""

from __future__ import annotations

from collections.abc import Iterable

from .models import ToolDefinition


class ToolRegistry:
    """Catalogo centralizado de herramientas disponibles."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register(self, definition: ToolDefinition):
        if definition.metadata.enabled:
            self._tools[definition.name] = definition

            for alias in definition.metadata.aliases:
                self._aliases[alias] = definition.name

    def register_many(self, definitions: Iterable[ToolDefinition]):
        for definition in definitions:
            self.register(definition)

    def get(self, name: str) -> ToolDefinition | None:
        canonical_name = self._aliases.get(name, name)
        return self._tools.get(canonical_name)

    def require(self, name: str) -> ToolDefinition:
        definition = self.get(name)

        if definition is None:
            available = ", ".join(self.names())
            raise KeyError(f"Tool no encontrada: {name}. Disponibles: {available}")

        return definition

    def names(self) -> list[str]:
        return sorted([*self._tools.keys(), *self._aliases.keys()])

    def definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def schemas(self, categories: set[str] | None = None) -> list[dict]:
        definitions = self.definitions()

        if categories is not None:
            definitions = [
                definition
                for definition in definitions
                if definition.metadata.category in categories
            ]

        return [definition.openai_schema() for definition in definitions]

    def search(
        self,
        *,
        category: str | None = None,
        tags: set[str] | None = None,
        capabilities: set[str] | None = None,
    ) -> list[ToolDefinition]:
        matches = self.definitions()

        if category:
            matches = [
                definition
                for definition in matches
                if definition.metadata.category == category
            ]

        if tags:
            matches = [
                definition
                for definition in matches
                if tags.intersection(definition.metadata.tags)
            ]

        if capabilities:
            matches = [
                definition
                for definition in matches
                if capabilities.intersection(definition.metadata.capabilities)
            ]

        return matches
