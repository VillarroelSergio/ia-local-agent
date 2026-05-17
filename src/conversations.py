"""Gestion de sesiones y conversaciones."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4


@dataclass
class Message:
    role: str
    content: str | None
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    metadata: dict = field(default_factory=dict)
    tool_calls: list | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_provider_dict(self):
        message = {
            "role": self.role,
            "content": self.content,
        }

        if self.tool_calls is not None:
            message["tool_calls"] = self.tool_calls

        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id

        if self.name is not None:
            message["name"] = self.name

        return message


@dataclass
class Conversation:
    id: str = field(default_factory=lambda: uuid4().hex)
    title: str = "Nueva conversacion"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    messages: list[Message] = field(default_factory=list)
    summary: str = ""


class ConversationStore:
    """Persistencia JSON simple para conversaciones.

    La interfaz queda preparada para migrar a SQLite sin tocar el orquestador.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_all(self):
        if not self.path.exists():
            return {}

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        conversations = {}

        for item in raw.get("conversations", []):
            messages = [Message(**message) for message in item.get("messages", [])]
            item["messages"] = messages
            conversation = Conversation(**item)
            conversations[conversation.id] = conversation

        return conversations

    def save_all(self, conversations):
        payload = {
            "conversations": [
                asdict(conversation)
                for conversation in conversations.values()
            ]
        }
        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


class ConversationManager:
    """Gestiona la conversacion activa y su historial."""

    def __init__(self, store):
        self.store = store
        self.conversations = store.load_all()
        self.active_conversation = None

    def create_conversation(self, title="Nueva conversacion"):
        conversation = Conversation(title=title)
        self.conversations[conversation.id] = conversation
        self.active_conversation = conversation
        self.save()
        return conversation

    def get_active(self):
        if self.active_conversation is None:
            return self.create_conversation()

        return self.active_conversation

    def append(self, message):
        conversation = self.get_active()
        conversation.messages.append(message)
        conversation.updated_at = datetime.now().isoformat(timespec="seconds")
        self.save()
        return message

    def remove_messages_after(self, length):
        conversation = self.get_active()
        del conversation.messages[length:]
        self.save()

    def current_length(self):
        return len(self.get_active().messages)

    def get_messages(self):
        return self.get_active().messages

    def save(self):
        self.store.save_all(self.conversations)
