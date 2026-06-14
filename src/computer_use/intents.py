"""Deterministic routing for natural-language Computer Use requests."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class ComputerUseIntent:
    tool_name: str
    arguments: dict
    user_message: str
    requires_confirmation: bool = False


_FIND_CONTROL = re.compile(
    r"^(?:busca|buscar|encuentra|localiza)\s+(?:el|la|un|una)?\s*"
    r"(?:boton|control|campo|menu)?\s*(?P<name>.+?)"
    r"(?:\s+en\s+la\s+ventana\s+activa)?(?:,\s*pero\s+no\s+lo\s+pulses)?[.\s]*$",
    re.IGNORECASE,
)
_WRITE_TEXT = re.compile(
    r"^(?:escribe|escribir|introduce|introducir)\s+[\"']?(?P<text>.+?)[\"']?\s+"
    r"(?:en|dentro de)\s+(?:el|la)?\s*(?P<name>documento|editor|campo|texto).*$",
    re.IGNORECASE,
)
_CLICK_CONTROL = re.compile(
    r"^(?:pulsa|pulsar|haz clic en|presiona)\s+(?:el|la)?\s*"
    r"(?:boton|control|menu)?\s*(?P<name>.+?)[.\s]*$",
    re.IGNORECASE,
)
_EMBEDDED_WRITE_TEXT = re.compile(
    r"\b(?:escribe|introduce)\s+[\"'](?P<text>.+?)[\"']\s+"
    r"(?:en|dentro de)\s+(?:el|la)?\s*(?P<name>documento|editor|campo|texto)\b",
    re.IGNORECASE,
)


def detect_computer_use_intent(message: str) -> ComputerUseIntent | None:
    text = _normalize(" ".join((message or "").strip().lower().split()))
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

    if (
        any(app in text for app in ("notepad", "bloc de notas"))
        and any(action in text for action in ("abre", "analiza", "observa", "escribe", "guardar", "pulsa"))
        and (
            ("abre" in text and "." in message)
            or sum(action in text for action in ("abre", "analiza", "observa", "escribe", "guardar", "pulsa")) > 1
        )
    ):
        return ComputerUseIntent(
            "computer_use",
            {"goal": message.strip(), "max_iterations": 3},
            "Iniciando una sesion Computer Use para completar el objetivo en Notepad.",
        )

    match = _WRITE_TEXT.match(text) or _EMBEDDED_WRITE_TEXT.search(text)
    if match:
        return ComputerUseIntent(
            "fill_text_field",
            {"name": match.group("name").strip(), "text": match.group("text").strip(" \"'")},
            "Necesito tu confirmacion antes de escribir en la ventana activa.",
            True,
        )

    match = _CLICK_CONTROL.match(text)
    if match:
        return ComputerUseIntent(
            "click_ui_control",
            {"name": match.group("name").strip(" .")},
            "Necesito tu confirmacion antes de invocar ese control.",
            True,
        )

    match = _FIND_CONTROL.match(text)
    if match and any(word in text for word in ("boton", "control", "campo", "menu")):
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
        and any(phrase in text for phrase in ("ventana activa", "su ventana", "la ventana"))
    ):
        return ComputerUseIntent(
            "observe_window",
            {"include_ocr": False},
            "Analizando la ventana activa sin OCR.",
        )

    return None


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))
