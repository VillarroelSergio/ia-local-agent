"""Gestion de sesiones y conversaciones con persistencia SQLite."""

import json
import sqlite3
from dataclasses import dataclass, field
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
    conversation_id: str | None = None

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


class SQLiteConversationStore:
    """Repositorio SQLite para conversaciones y mensajes."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT ''
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    tool_calls_json TEXT,
                    tool_call_id TEXT,
                    name TEXT,
                    position INTEGER NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_position
                ON messages(conversation_id, position)
            """)

    def load_all(self):
        conversations = {}

        with self.connect() as connection:
            conversation_rows = connection.execute(
                "SELECT * FROM conversations ORDER BY updated_at"
            ).fetchall()

            for row in conversation_rows:
                conversation = Conversation(
                    id=row["id"],
                    title=row["title"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    summary=row["summary"],
                    messages=[],
                )
                message_rows = connection.execute(
                    """
                    SELECT * FROM messages
                    WHERE conversation_id = ?
                    ORDER BY position
                    """,
                    (conversation.id,),
                ).fetchall()

                for message_row in message_rows:
                    conversation.messages.append(self.row_to_message(message_row))

                conversations[conversation.id] = conversation

        return conversations

    def save_conversation(self, conversation):
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at, summary)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    updated_at = excluded.updated_at,
                    summary = excluded.summary
                """,
                (
                    conversation.id,
                    conversation.title,
                    conversation.created_at,
                    conversation.updated_at,
                    conversation.summary,
                ),
            )

    def append_message(self, conversation, message):
        message.conversation_id = conversation.id
        position = len(conversation.messages) - 1

        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO messages (
                    id, conversation_id, role, content, created_at, metadata_json,
                    tool_calls_json, tool_call_id, name, position
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    conversation.id,
                    message.role,
                    message.content,
                    message.created_at,
                    json.dumps(message.metadata, ensure_ascii=False),
                    json.dumps(message.tool_calls, ensure_ascii=False)
                    if message.tool_calls is not None else None,
                    message.tool_call_id,
                    message.name,
                    position,
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (conversation.updated_at, conversation.id),
            )

    def remove_messages_after(self, conversation, length):
        removed_ids = [message.id for message in conversation.messages[length:]]
        del conversation.messages[length:]
        conversation.updated_at = datetime.now().isoformat(timespec="seconds")

        if not removed_ids:
            return []

        placeholders = ", ".join("?" for _ in removed_ids)

        with self.connect() as connection:
            connection.execute(
                f"DELETE FROM messages WHERE id IN ({placeholders})",
                removed_ids,
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (conversation.updated_at, conversation.id),
            )

        return removed_ids

    def save_all(self, conversations):
        for conversation in conversations.values():
            self.save_conversation(conversation)

    def row_to_message(self, row):
        return Message(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"] or "{}"),
            tool_calls=json.loads(row["tool_calls_json"])
            if row["tool_calls_json"] else None,
            tool_call_id=row["tool_call_id"],
            name=row["name"],
        )


ConversationStore = SQLiteConversationStore


class ConversationManager:
    """Gestiona la conversacion activa y su historial."""

    def __init__(self, store):
        self.store = store
        self.conversations = store.load_all()
        self.active_conversation = self.get_last_conversation()

    def get_last_conversation(self):
        if not self.conversations:
            return None

        return max(
            self.conversations.values(),
            key=lambda conversation: conversation.updated_at,
        )

    def create_conversation(self, title="Nueva conversacion"):
        conversation = Conversation(title=title)
        self.conversations[conversation.id] = conversation
        self.active_conversation = conversation
        self.store.save_conversation(conversation)
        return conversation

    def get_active(self):
        if self.active_conversation is None:
            return self.create_conversation()

        return self.active_conversation

    def append(self, message):
        conversation = self.get_active()
        message.conversation_id = conversation.id
        conversation.messages.append(message)
        conversation.updated_at = datetime.now().isoformat(timespec="seconds")
        self.store.save_conversation(conversation)
        self.store.append_message(conversation, message)
        return message

    def remove_messages_after(self, length):
        conversation = self.get_active()
        return self.store.remove_messages_after(conversation, length)

    def current_length(self):
        return len(self.get_active().messages)

    def get_messages(self):
        return self.get_active().messages

    def save(self):
        self.store.save_all(self.conversations)
