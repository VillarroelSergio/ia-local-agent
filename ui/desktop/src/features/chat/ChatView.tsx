import { FormEvent, useEffect, useRef, useState } from "react";
import { Send, Square } from "lucide-react";
import type { ChatMessage } from "../../types/api";
import { MessageBubble } from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  busy: boolean;
  activeConversationId?: string;
  onSend: (message: string) => void;
  onCancel: () => void;
}

/** Renderiza el area de mensajes y el composer para enviar o cancelar respuestas del chat. */
export function ChatView({ messages, busy, activeConversationId, onSend, onCancel }: Props) {
  const [draft, setDraft] = useState("");
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  /** Valida el borrador, limpia el textarea y delega el envio al contenedor principal. */
  function submit(event: FormEvent) {
    event.preventDefault();
    const value = draft.trim();
    if (!value || busy) return;
    setDraft("");
    onSend(value);
  }

  return (
    <main className="chat-shell">
      <div className="messages" ref={scroller}>
        {messages.length === 0 ? (
          <div className="empty-chat">
            <h1>IA Local Agent</h1>
            <p>{activeConversationId ? "Empieza escribiendo abajo." : "Crea o selecciona una conversacion."}</p>
          </div>
        ) : (
          messages.map((message, index) => <MessageBubble key={message.id ?? index} message={message} />)
        )}
      </div>
      <form className="composer" onSubmit={submit}>
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Mensaje para el agente local"
          rows={1}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) submit(event);
          }}
        />
        {busy ? (
          <button type="button" className="icon-button stop" title="Cancelar" onClick={onCancel}>
            <Square size={18} />
          </button>
        ) : (
          <button type="submit" className="icon-button send" title="Enviar" disabled={!draft.trim()}>
            <Send size={18} />
          </button>
        )}
      </form>
    </main>
  );
}
