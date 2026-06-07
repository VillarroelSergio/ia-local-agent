import type { TimelineEvent } from "../../types/api";

interface AuditItem {
  title: string;
  detail: string;
  tone: "neutral" | "success" | "warning" | "error";
  timestamp?: string;
}

/** Convierte eventos tecnicos recientes en una lista auditiva legible para el usuario. */
export function TimelinePanel({ events }: { events: TimelineEvent[] }) {
  const auditItems = events.map(toAuditItem).filter(Boolean).slice(0, 80) as AuditItem[];

  return (
    <section className="timeline-panel">
      <div className="panel-heading">
        <h2>Actividad</h2>
        <span>{auditItems.length}</span>
      </div>
      <div className="timeline-list audit-list" data-testid="timeline-list">
        {auditItems.length === 0 && <div className="empty-panel">Aun no hay actividad.</div>}
        {auditItems.map((item, index) => (
          <article key={`${item.title}-${index}`} className={`audit-event ${item.tone}`}>
            <div className="audit-dot" />
            <div>
              <div className="audit-title">{item.title}</div>
              <p>{item.detail}</p>
              <small>{formatTime(item.timestamp)}</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

/** Normaliza un evento del backend en un item visual de auditoria o lo descarta si no aporta valor. */
function toAuditItem(event: TimelineEvent): AuditItem | null {
  const data = event.data ?? event.payload ?? {};
  const toolName = humanize(String(data.name ?? data.tool_name ?? data.tool ?? ""));
  const conversation = String(data.conversation_id ?? "").slice(0, 8);

  switch (event.type) {
    case "message.started":
      return { title: "El modelo empezo a pensar", detail: conversation ? `Conversacion ${conversation}` : "Preparando contexto.", tone: "neutral", timestamp: event.timestamp };
    case "message.completed":
      return { title: "Respuesta completada", detail: "El asistente termino su mensaje.", tone: "success", timestamp: event.timestamp };
    case "tool.requested":
      return { title: "El modelo pidio una tool", detail: toolName || "Solicitud de herramienta.", tone: "warning", timestamp: event.timestamp };
    case "tool.started":
      return { title: "Tool en ejecucion", detail: toolName || "Ejecutando herramienta.", tone: "neutral", timestamp: event.timestamp };
    case "tool.completed":
      return { title: "Tool completada", detail: toolName || "La herramienta termino correctamente.", tone: "success", timestamp: event.timestamp };
    case "tool.confirmation_required":
      return { title: "Confirmacion requerida", detail: toolName ? `${toolName} necesita tu permiso.` : "Una accion necesita permiso.", tone: "warning", timestamp: event.timestamp };
    case "tool.confirmed":
      return { title: "Confirmacion aprobada", detail: toolName || "Se autorizo la accion.", tone: "success", timestamp: event.timestamp };
    case "tool.rejected":
      return { title: "Confirmacion rechazada", detail: toolName || "Se rechazo la accion.", tone: "warning", timestamp: event.timestamp };
    case "tool.failed":
      return { title: "Tool con error", detail: toolName || "La herramienta no pudo completarse.", tone: "error", timestamp: event.timestamp };
    case "workflow.started":
      return { title: "Workflow iniciado", detail: "El agente empezo un flujo de trabajo.", tone: "neutral", timestamp: event.timestamp };
    case "workflow.finished":
      return { title: "Workflow terminado", detail: "El flujo de trabajo termino.", tone: "success", timestamp: event.timestamp };
    case "error":
      return { title: "Error", detail: String(data.message ?? "Ha ocurrido un error."), tone: "error", timestamp: event.timestamp };
    default:
      if (event.type.includes("windows")) {
        return { title: "Evento de Windows", detail: humanize(event.type), tone: "neutral", timestamp: event.timestamp };
      }
      return null;
  }
}

/** Transforma identificadores tecnicos en texto capitalizado para la actividad. */
function humanize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

/** Formatea timestamps ISO a hora local, manteniendo el texto original si no es una fecha valida. */
function formatTime(timestamp?: string) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleTimeString();
}
