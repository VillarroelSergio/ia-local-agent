"""Deterministic routing for natural-language Computer Use requests."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ComputerUseIntent:
    tool_name: str
    arguments: dict
    user_message: str
    requires_confirmation: bool = False


_FIND_CONTROL = re.compile(
    r"^(?:busca|buscar|encuentra|localiza)\s+(?:el|la|un|una)?\s*"
    r"(?:boton|botón|control|campo|menu|menú)?\s*(?P<name>.+?)"
    r"(?:\s+en\s+la\s+ventana\s+activa)?(?:,\s*pero\s+no\s+lo\s+pulses)?[.\s]*$",
    re.IGNORECASE,
)


def detect_computer_use_intent(message: str) -> ComputerUseIntent | None:
    text = " ".join((message or "").strip().lower().split())
    if not text:
        return None

    if any(phrase in text for phrase in (
        "organiza mis ventanas", "organizar mis ventanas", "ordena mis ventanas",
        "organiza las ventanas", "organizar las ventanas",
    )):
        return ComputerUseIntent(
            "tile_windows_layout",
            {"layout": "horizontal", "queries": [], "handles": []},
            "Necesito tu confirmacion para organizar las ventanas.",
            True,
        )

    match = _FIND_CONTROL.match(text)
    if match and any(word in text for word in ("boton", "botón", "control", "campo", "menu", "menú")):
        name = re.sub(r"\s*,?\s*pero\s+no\s+lo\s+pulses.*$", "", match.group("name"), flags=re.IGNORECASE)
        return ComputerUseIntent(
            "find_ui_control",
            {"name": name.strip(" .")},
            f"Buscando el control {name.strip(' .')} sin interactuar con el.",
        )

    if any(phrase in text for phrase in (
        "extrae el texto visible", "extraer el texto visible", "lee el texto visible",
        "leer el texto visible", "lee todo el contenido", "leer todo el contenido",
    )):
        return ComputerUseIntent(
            "observe_window",
            {"include_ocr": False},
            "Leyendo el texto accesible de la ventana activa sin OCR.",
        )

    if (
        any(word in text for word in ("analiza", "analizar", "observa", "observar", "resume", "resumir"))
        and "ventana activa" in text
    ):
        return ComputerUseIntent(
            "observe_window",
            {"include_ocr": False},
            "Analizando la ventana activa sin OCR.",
        )

    return None
