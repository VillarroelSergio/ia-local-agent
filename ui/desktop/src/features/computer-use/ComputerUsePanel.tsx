import { Bot, Eye, RefreshCw, Square } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../../services/apiClient";
import type { ComputerUseObservation, ComputerUseSession, TimelineEvent } from "../../types/api";

interface Props {
  onEvent: (event: Record<string, unknown>) => void;
}

export function ComputerUsePanel({ onEvent }: Props) {
  const [goal, setGoal] = useState("Observa el estado actual");
  const [running, setRunning] = useState(false);
  const [session, setSession] = useState<ComputerUseSession | null>(null);
  const [sessions, setSessions] = useState<ComputerUseSession[]>([]);
  const [observation, setObservation] = useState<ComputerUseObservation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentAction = useMemo(() => {
    const last = session?.actions?.[session.actions.length - 1];
    if (!last) return "Sin accion";
    if ("verification" in last) return "Verificando resultado";
    if ("execution" in last) return "Ejecutando workflow";
    return "Actualizando estado";
  }, [session]);

  async function refreshSessions() {
    const response = await apiClient.listComputerUseSessions(8);
    setSessions(response.sessions);
  }

  async function observe(includeOcr = false) {
    setError(null);
    try {
      const result = await apiClient.observeComputerUse(includeOcr);
      setObservation(result);
      onEvent({ type: "computer_use.observed", timestamp: new Date().toISOString(), data: { summary: result.screen_summary } });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function runGoal() {
    if (!goal.trim()) return;
    setRunning(true);
    setError(null);
    try {
      onEvent({ type: "computer_use.started", timestamp: new Date().toISOString(), data: { goal } });
      const result = await apiClient.runComputerUse(goal, 3);
      setSession(result);
      await refreshSessions();
      onEvent({ type: `computer_use.${result.status}`, timestamp: new Date().toISOString(), data: { session_id: result.id, goal: result.goal } });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      onEvent({ type: "computer_use.failed", timestamp: new Date().toISOString(), data: { message } });
    } finally {
      setRunning(false);
    }
  }

  async function cancel() {
    if (!session) return;
    const result = await apiClient.cancelComputerUseSession(session.id);
    onEvent({ type: "computer_use.cancelled", timestamp: new Date().toISOString(), data: result });
    await refreshSessions();
  }

  useEffect(() => {
    refreshSessions().catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <section className="computer-use-panel">
      <div className="panel-heading">
        <h2>Computer Use</h2>
        <button className="mini-button" onClick={() => refreshSessions()} title="Actualizar sesiones">
          <RefreshCw size={14} />
        </button>
      </div>

      <label>
        Objetivo
        <textarea value={goal} onChange={(event) => setGoal(event.target.value)} rows={3} />
      </label>

      <div className="computer-actions">
        <button className="primary-action" onClick={runGoal} disabled={running}>
          <Bot size={16} />
          Ejecutar
        </button>
        <button className="secondary-action" onClick={() => observe(false)} disabled={running}>
          <Eye size={16} />
          Observar
        </button>
        <button className="danger-action" onClick={cancel} disabled={!session || running}>
          <Square size={14} />
          Cancelar
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="computer-status-grid">
        <div>
          <span>Estado</span>
          <strong>{session?.status ?? "idle"}</strong>
        </div>
        <div>
          <span>Accion</span>
          <strong>{currentAction}</strong>
        </div>
      </div>

      <div className="computer-section">
        <h3>Observacion</h3>
        <p>{observation?.screen_summary || session?.observations?.at(-1)?.screen_summary?.toString() || "Sin observacion reciente."}</p>
        <small>{formatSources(observation?.used_sources ?? (session?.observations?.at(-1)?.used_sources as string[] | undefined))}</small>
      </div>

      <div className="computer-section">
        <h3>Resultado</h3>
        <p>{session?.error || summarizeLastAction(session) || "Sin resultado."}</p>
      </div>

      <div className="computer-section">
        <h3>Sesiones</h3>
        <div className="computer-session-list">
          {sessions.length === 0 && <div className="empty-panel">No hay sesiones.</div>}
          {sessions.map((item) => (
            <button key={item.id} onClick={() => setSession(item)}>
              <strong>{item.goal}</strong>
              <span>{item.status} · {new Date(item.updated_at).toLocaleTimeString()}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function summarizeLastAction(session: ComputerUseSession | null) {
  const last = session?.actions?.[session.actions.length - 1];
  if (!last) return "";
  if ("verification" in last) {
    const verification = last.verification as Record<string, unknown>;
    return String(verification.reason ?? "Verificacion registrada.");
  }
  if ("execution" in last) {
    const execution = last.execution as Record<string, unknown>;
    return execution.ok ? "Ejecucion completada." : "La ejecucion necesita revision.";
  }
  return "Accion registrada.";
}

function formatSources(sources?: string[]) {
  return sources?.length ? `Fuentes: ${sources.join(", ")}` : "Fuentes: WindowManager";
}
