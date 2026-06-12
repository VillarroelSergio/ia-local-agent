import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../../types/api";

/** Muestra un mensaje individual del chat con etiqueta por rol y contenido Markdown. */
export function MessageBubble({ message }: { message: ChatMessage }) {
  const label = message.role === "assistant" ? "IA" : message.role === "user" ? "Tu" : message.name ?? message.role;
  return (
    <article className={`message ${message.role}${message.metadata?.error ? " error" : ""}`} data-testid={`message-${message.role}`}>
      <div className="message-label">{label}</div>
      <div className="message-content">
        {message.content ? <ReactMarkdown>{message.content}</ReactMarkdown> : <span className="muted">Sin contenido</span>}
      </div>
    </article>
  );
}
