"""Memoria persistente simple para el agente local.

Este modulo guarda recuerdos del usuario en un archivo JSON local. Es una
primera capa de memoria explicita: el usuario decide que recordar con comandos
como /remember, y el agente inyecta esos recuerdos en el prompt del sistema.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_MEMORY_ITEMS_IN_PROMPT = 20


def get_memory_path():
    """Devuelve la ruta actual de memoria desde el entorno."""
    return PROJECT_ROOT / os.getenv("MEMORY_PATH", "data/memory.json")


def ensure_memory_file():
    """Crea la carpeta y el archivo de memoria si todavia no existen."""
    memory_path = get_memory_path()
    memory_path.parent.mkdir(parents=True, exist_ok=True)

    if not memory_path.exists():
        memory_path.write_text("[]", encoding="utf-8")


def load_memories():
    """Carga todas las memorias persistentes desde disco.

    Si el archivo no existe, esta corrupto o no contiene una lista JSON, devuelve
    una lista vacia para que el agente pueda seguir funcionando.
    """
    ensure_memory_file()

    try:
        memories = json.loads(get_memory_path().read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(memories, list):
        return []

    return memories


def save_memories(memories):
    """Guarda la lista completa de memorias en formato JSON legible."""
    ensure_memory_file()
    get_memory_path().write_text(
        json.dumps(memories, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def remember(content):
    """Guarda un nuevo recuerdo y devuelve el registro creado."""
    content = content.strip()

    if not content:
        return {"error": "No hay contenido para recordar."}

    memories = load_memories()
    memory = {
        "id": uuid4().hex[:8],
        "content": content,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    memories.append(memory)
    save_memories(memories)
    return memory


def forget(memory_id):
    """Elimina una memoria por id corto y devuelve el resultado."""
    memories = load_memories()
    remaining_memories = [
        memory for memory in memories
        if memory.get("id") != memory_id
    ]

    if len(remaining_memories) == len(memories):
        return {"error": f"No existe una memoria con id: {memory_id}"}

    save_memories(remaining_memories)
    return {"deleted": memory_id}


def format_memories_for_prompt():
    """Convierte las memorias recientes en texto listo para el system prompt."""
    memories = load_memories()

    if not memories:
        return "No hay memoria persistente guardada todavia."

    recent_memories = memories[-MAX_MEMORY_ITEMS_IN_PROMPT:]
    lines = [
        f"- [{memory.get('id')}] {memory.get('content')}"
        for memory in recent_memories
    ]

    return "\n".join(lines)
