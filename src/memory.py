import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_PATH = PROJECT_ROOT / "data" / "memory.json"
MAX_MEMORY_ITEMS_IN_PROMPT = 20


def ensure_memory_file():
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text("[]", encoding="utf-8")


def load_memories():
    ensure_memory_file()

    try:
        memories = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(memories, list):
        return []

    return memories


def save_memories(memories):
    ensure_memory_file()
    MEMORY_PATH.write_text(
        json.dumps(memories, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def remember(content):
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
    memories = load_memories()

    if not memories:
        return "No hay memoria persistente guardada todavia."

    recent_memories = memories[-MAX_MEMORY_ITEMS_IN_PROMPT:]
    lines = [
        f"- [{memory.get('id')}] {memory.get('content')}"
        for memory in recent_memories
    ]

    return "\n".join(lines)
