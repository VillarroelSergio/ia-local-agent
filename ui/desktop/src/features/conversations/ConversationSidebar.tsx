import { Edit3, Plus, Trash2 } from "lucide-react";
import type { Conversation } from "../../types/api";

interface Props {
  conversations: Conversation[];
  activeId?: string;
  loading?: boolean;
  onNew: () => void;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}

export function ConversationSidebar({ conversations, activeId, loading, onNew, onSelect, onRename, onDelete }: Props) {
  return (
    <aside className="sidebar">
      <button className="new-chat" onClick={onNew}>
        <Plus size={17} />
        Nueva conversacion
      </button>
      <div className="conversation-list" aria-label="Conversaciones">
        {loading && <div className="muted-row">Cargando...</div>}
        {conversations.map((conversation) => (
          <div key={conversation.id} className={`conversation-row ${conversation.id === activeId ? "active" : ""}`}>
            <button className="conversation-title" onClick={() => onSelect(conversation.id)}>
              <span>{conversation.title || "Sin titulo"}</span>
              <small>{conversation.message_count} mensajes</small>
            </button>
            <button
              className="mini-button"
              title="Renombrar"
              onClick={() => {
                const title = window.prompt("Nuevo titulo", conversation.title);
                if (title?.trim()) onRename(conversation.id, title.trim());
              }}
            >
              <Edit3 size={14} />
            </button>
            <button
              className="mini-button danger"
              title="Borrar"
              onClick={() => window.confirm("Borrar conversacion?") && onDelete(conversation.id)}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
