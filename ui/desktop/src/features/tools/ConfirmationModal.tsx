import type { ConfirmationPayload } from "../../types/api";

interface Props {
  payload: ConfirmationPayload | null;
  busy?: boolean;
  onConfirm: () => void;
  onReject: () => void;
}

/** Muestra una confirmacion bloqueante para aprobar o rechazar la ejecucion de una tool sensible. */
export function ConfirmationModal({ payload, busy, onConfirm, onReject }: Props) {
  if (!payload) return null;
  const targetWindow = findWindowPayload(payload.arguments);
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal confirmation-modal">
        <h2>Confirmar tool</h2>
        <p className="danger-copy">Esta accion sera validada por el backend. Revisa los argumentos antes de continuar.</p>
        <dl>
          <dt>Tool</dt>
          <dd>{payload.tool_name}</dd>
          <dt>Risk level</dt>
          <dd>{payload.risk_level ?? "No informado"}</dd>
          <dt>Policy</dt>
          <dd>{payload.policy_decision ?? payload.reason ?? "Confirmacion requerida"}</dd>
          {targetWindow && (
            <>
              <dt>Ventana</dt>
              <dd>{String(targetWindow.title ?? "Sin titulo")} ({String(targetWindow.process_name ?? "proceso desconocido")})</dd>
            </>
          )}
        </dl>
        <pre>{JSON.stringify(payload.arguments, null, 2)}</pre>
        <div className="modal-actions">
          <button className="secondary-action" disabled={busy} onClick={onReject}>
            Rechazar
          </button>
          <button className="danger-action" disabled={busy} onClick={onConfirm}>
            Confirmar ejecucion
          </button>
        </div>
      </div>
    </div>
  );
}

function findWindowPayload(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  if (record.active_window && typeof record.active_window === "object") return record.active_window as Record<string, unknown>;
  if ("handle" in record && ("title" in record || "process_name" in record)) return record;
  for (const child of Object.values(record)) {
    const found = findWindowPayload(child);
    if (found) return found;
  }
  return null;
}
