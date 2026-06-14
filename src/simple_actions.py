"""Deterministic command routing for common desktop actions.

The router is intentionally small and explicit. It gives the UI, CLI and future
voice layer a stable path for common commands without depending on LLM tool
selection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import quote_plus


class CommandIntent(StrEnum):
    OPEN_URL = "open_url"
    OPEN_APP = "open_app"
    SEARCH_WEB = "search_web"
    SEARCH_YOUTUBE = "search_youtube"
    SEARCH_SPOTIFY = "search_spotify"
    MEDIA_CONTROL = "media_control"
    VOLUME_CONTROL = "volume_control"
    WINDOW_CONTROL = "window_control"


@dataclass(frozen=True)
class SimpleAction:
    tool_name: str
    arguments: dict
    user_message: str
    intent: CommandIntent
    confidence: float = 1.0


_OPEN_PREFIX_RE = re.compile(
    r"^(?:por favor\s+)?(?:abre|abrir|abrelo|abrela|open|launch|inicia|iniciar|arranca|arrancar)\s+",
    re.IGNORECASE,
)
_SEARCH_RE = re.compile(r"^(?:busca|buscar|search)\s+(.+)$", re.IGNORECASE)
_WINDOW_RE = re.compile(
    r"^(?P<verb>enfoca|enfocar|maximiza|maximizar|minimiza|minimizar)\s+(?P<target>.+)$",
    re.IGNORECASE,
)

_WEB_SHORTCUTS = {
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "youtube": "https://www.youtube.com",
    "spotify web": "https://open.spotify.com",
}

_MEDIA_KEYS = {
    "pausa": ("playpause", "Pausando o reanudando la reproduccion."),
    "pausar": ("playpause", "Pausando o reanudando la reproduccion."),
    "reproduce": ("playpause", "Pausando o reanudando la reproduccion."),
    "reproducir": ("playpause", "Pausando o reanudando la reproduccion."),
    "continua": ("playpause", "Pausando o reanudando la reproduccion."),
    "continuar": ("playpause", "Pausando o reanudando la reproduccion."),
    "play": ("playpause", "Pausando o reanudando la reproduccion."),
    "pause": ("playpause", "Pausando o reanudando la reproduccion."),
    "siguiente": ("nexttrack", "Pasando a la siguiente pista."),
    "next": ("nexttrack", "Pasando a la siguiente pista."),
    "anterior": ("prevtrack", "Volviendo a la pista anterior."),
    "previa": ("prevtrack", "Volviendo a la pista anterior."),
    "previous": ("prevtrack", "Volviendo a la pista anterior."),
}

_VOLUME_KEYS = {
    "sube el volumen": ("volumeup", "Subiendo el volumen."),
    "subir volumen": ("volumeup", "Subiendo el volumen."),
    "baja el volumen": ("volumedown", "Bajando el volumen."),
    "bajar volumen": ("volumedown", "Bajando el volumen."),
    "silencia": ("volumemute", "Alternando silencio."),
    "silenciar": ("volumemute", "Alternando silencio."),
    "mute": ("volumemute", "Alternando silencio."),
}


def detect_simple_action(message: str) -> SimpleAction | None:
    text = _normalize(message)
    if not text:
        return None

    media_action = _detect_media_or_volume(text)
    if media_action:
        return media_action

    window_action = _detect_window_action(text)
    if window_action:
        return window_action

    search_match = _SEARCH_RE.match(text)
    if search_match:
        query, provider = _split_search_provider(search_match.group(1).strip())
        if query:
            return _search_action(query, provider)

    open_target = _extract_open_target(text)
    if not open_target:
        return None

    if open_target.startswith(("http://", "https://")):
        return SimpleAction("open_url", {"url": open_target}, f"Abriendo {open_target}.", CommandIntent.OPEN_URL)

    if open_target in _WEB_SHORTCUTS:
        return SimpleAction("open_url", {"url": _WEB_SHORTCUTS[open_target]}, f"Abriendo {open_target}.", CommandIntent.OPEN_URL)

    if open_target.startswith("google ") or open_target.startswith("google:"):
        query = open_target.removeprefix("google").lstrip(" :")
        if query:
            return _search_action(query, "google")

    return SimpleAction(
        "open_application",
        {"app_name": _canonical_app_name(open_target)},
        f"Abriendo {open_target}.",
        CommandIntent.OPEN_APP,
    )


def _detect_media_or_volume(text: str) -> SimpleAction | None:
    for phrase, (key, message) in _VOLUME_KEYS.items():
        if text == phrase or phrase in text:
            return SimpleAction("press_key", {"key": key}, message, CommandIntent.VOLUME_CONTROL)

    for phrase, (key, message) in _MEDIA_KEYS.items():
        if text == phrase or text.startswith(f"{phrase} "):
            return SimpleAction("press_key", {"key": key}, message, CommandIntent.MEDIA_CONTROL)

    return None


def _detect_window_action(text: str) -> SimpleAction | None:
    match = _WINDOW_RE.match(text)
    if not match:
        return None

    verb = match.group("verb")
    target = _strip_articles(match.group("target").strip(" ."))
    tool_by_verb = {
        "enfoca": ("focus_window", "Enfocando"),
        "enfocar": ("focus_window", "Enfocando"),
        "maximiza": ("maximize_window", "Maximizando"),
        "maximizar": ("maximize_window", "Maximizando"),
        "minimiza": ("minimize_window", "Minimizando"),
        "minimizar": ("minimize_window", "Minimizando"),
    }
    tool_name, label = tool_by_verb[verb]
    return SimpleAction(
        tool_name,
        {"query": _canonical_app_name(target)},
        f"{label} {target}.",
        CommandIntent.WINDOW_CONTROL,
    )


def _split_search_provider(raw_query: str) -> tuple[str, str]:
    query = raw_query.strip(" .")
    for marker, provider in (
        (" en youtube", "youtube"),
        (" en spotify", "spotify"),
        (" en google", "google"),
        (" en internet", "google"),
        (" en la web", "google"),
    ):
        if query.endswith(marker):
            return query[: -len(marker)].strip(), provider
    return query, "google"


def _search_action(query: str, provider: str) -> SimpleAction:
    providers = {
        "google": (
            "https://www.google.com/search?q={query}",
            "Google",
            CommandIntent.SEARCH_WEB,
        ),
        "youtube": (
            "https://www.youtube.com/results?search_query={query}",
            "YouTube",
            CommandIntent.SEARCH_YOUTUBE,
        ),
        "spotify": (
            "https://open.spotify.com/search/{query}",
            "Spotify",
            CommandIntent.SEARCH_SPOTIFY,
        ),
    }
    template, label, intent = providers.get(provider, providers["google"])
    encoded = quote_plus(query)
    if provider == "spotify":
        encoded = quote_plus(query).replace("+", "%20")
    url = template.format(query=encoded)
    return SimpleAction("open_url", {"url": url}, f"Buscando {query} en {label}.", intent)


def _extract_open_target(text: str) -> str | None:
    match = _OPEN_PREFIX_RE.match(text)
    if not match:
        return None
    target = text[match.end():].strip(" .")
    # Opening an application is a single-action shortcut. Compound desktop
    # requests must be handled by Computer Use instead of treating the whole
    # prompt as an application name.
    if _is_compound_open_request(target):
        return None
    target = _strip_articles(target)
    if target in {"navegador", "browser"}:
        target = "google"
    return target or None


def _is_compound_open_request(target: str) -> bool:
    return bool(
        re.search(r"[.;]\s+\w", target)
        or re.search(
            r"\b(?:cuando|despues|luego|y\s+(?:analiza|escribe|busca|pulsa|verifica|organiza))\b",
            target,
            re.IGNORECASE,
        )
    )


def _strip_articles(value: str) -> str:
    if value.startswith(("el ", "la ", "los ", "las ")):
        return value.split(" ", 1)[1]
    return value


def _canonical_app_name(target: str) -> str:
    aliases = {
        "visual studio code": "vscode",
        "vs code": "vscode",
        "codigo": "vscode",
        "bloc de notas": "notepad",
        "notas": "notepad",
        "calculadora": "calculator",
        "explorador": "explorer",
        "explorador de archivos": "explorer",
    }
    return aliases.get(target, target)


def _normalize(value: str) -> str:
    return " ".join((value or "").strip().lower().split())
