import { Bot, Check, Eye, RefreshCw, Square, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "../../services/apiClient";
import type {
  ComputerUseAction,
  ComputerUseConfirmation,
  ComputerUseObservation,
  ComputerUsePlanStep,
  ComputerUseSession,
} from "../../types/api";

interface Props {
  onEvent: (event: Record<string, unknown>) => void;
}

const ACTIVE_STATUSES = new Set(["created", "running", "waiting_confirmation"]);

export function ComputerUsePanel({ onEvent }: Props) {
  const [goal, setGoal] = useState("Observa el estado actual");
  const [session, setSession] = useState<ComputerUseSession | null>(null);
  const [sessions, setSessions] = useState<ComputerUseSession[]>([]);
  const [observation, setObservation] = useState<ComputerUseObservation | null>(null);
  const [operation, setOperation] = useState<"run" | "observe" | "cancel" | "confirm" | "refresh" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const plan = useMemo(() => getPlanSteps(session), [session]);
  const confirmation = useMemo(() => getPendingConfirmation(session), [session]);
  const progress = useMemo(() => getProgress(session, plan), [session, plan]);
  const isActive = Boolean(session && ACTIVE_STATUSES.has(session.status));

  async function refreshSessions(selectSessionId?: string) {
    const response = await apiClient.listComputerUseSessions(8);
    setSessions(response.sessions);
    const selectedId = selectSessionId ?? session?.id;
    if (selectedId) {
      const selected = response.sessions.find((item) => item.id === selectedId);
      if (selected) setSession(selected);
    }
    return response.sessions;
  }

  async function refreshAll() {
    setOperation("refresh");
    setError(null);
    try {
      if (session) {
        const latest = await apiClient.getComputerUseSession(session.id);
        setSession(latest);
      }
      await refreshSessions();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setOperation(null);
    }
  }

  async function observe(includeOcr = false) {
    setOperation("observe");
    setError(null);
    try {
      const result = await apiClient.observeComputerUse(includeOcr);
      setObservation(result);
      onEvent({ type: "computer_use.observed", timestamp: new Date().toISOString(), data: { summary: result.screen_summary } });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setOperation(null);
    }
  }

  async function runGoal() {
    const trimmedGoal = goal.trim();
    if (!trimmedGoal) {
      setError("Escribe un objetivo antes de ejecutar.");
      return;
    }
    setOperation("run");
    setError(null);
    try {
      onEvent({ type: "computer_use.started", timestamp: new Date().toISOString(), data: { goal: trimmedGoal } });
      const result = await apiClient.runComputerUse(trimmedGoal, 3);
      setSession(result);
      await refreshSessions(result.id);
      onEvent({ type: `computer_use.${result.status}`, timestamp: new Date().toISOString(), data: { session_id: result.id, goal: result.goal } });
    } catch (err) {
      const message = errorMessage(err);
      setError(message);
      onEvent({ type: "computer_use.failed", timestamp: new Date().toISOString(), data: { message } });
    } finally {
      setOperation(null);
    }
  }

  async function cancel() {
    if (!session) return;
    setOperation("cancel");
    setError(null);
    try {
      const result = await apiClient.cancelComputerUseSession(session.id);
      if (!result.cancelled) throw new Error("La sesion ya no estaba activa o no pudo cancelarse.");
      onEvent({ type: "computer_use.cancelled", timestamp: new Date().toISOString(), data: result });
      const latest = await apiClient.getComputerUseSession(session.id);
      setSession(latest);
      await refreshSessions(session.id);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setOperation(null);
    }
  }

  async function confirm(approved: boolean) {
    if (!session) return;
    setOperation("confirm");
    setError(null);
    try {
      const result = await apiClient.confirmComputerUseSession(session.id, approved);
      const latest = result.session ?? await apiClient.getComputerUseSession(session.id);
      setSession(latest);
      await refreshSessions(session.id);
      onEvent({
        type: approved ? "computer_use.confirmed" : "computer_use.rejected",
        timestamp: new Date().toISOString(),
        data: { session_id: session.id },
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setOperation(null);
    }
  }

  useEffect(() => {
    refreshSessions().catch((err) => setError(errorMessage(err)));
  }, []);

  useEffect(() => {
    if (!session || !ACTIVE_STATUSES.has(session.status) || operation) return;
    const timer = window.setTimeout(async () => {
      try {
        const latest = await apiClient.getComputerUseSession(session.id);
        setSession(latest);
        setSessions((current) => current.map((item) => item.id === latest.id ? latest : item));
      } catch (err) {
        setError(errorMessage(err));
      }
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [session, operation]);

  const recentObservation = observation ?? session?.observations.at(-1);

  return (
    <section className="computer-use-panel" aria-busy={operation !== null}>
      <div className="panel-heading">
        <h2>Computer Use</h2>
        <button className="mini-button" onClick={refreshAll} disabled={operation !== null} title="Actualizar sesiones" aria-label="Actualizar sesiones">
          <RefreshCw size={14} />
        </button>
      </div>

      <label>
        Objetivo
        <textarea value={goal} onChange={(event) => setGoal(event.target.value)} rows={3} disabled={operation === "run" || isActive} />
      </label>

      <div className="computer-actions">
        <button className="primary-action" onClick={runGoal} disabled={operation !== null || isActive || !goal.trim()}>
          <Bot size={16} />
          {operation === "run" ? "Ejecutando..." : "Ejecutar"}
        </button>
        <button className="secondary-action" onClick={() => observe(false)} disabled={operation !== null || isActive}>
          <Eye size={16} />
          {operation === "observe" ? "Observando..." : "Observar"}
        </button>
        <button className="danger-action" onClick={cancel} disabled={operation !== null || !isActive} title="Cancelar sesion" aria-label="Cancelar sesion">
          <Square size={14} />
        </button>
      </div>

      {error && <div className="error-box" role="alert">{error}</div>}

      <div className="computer-status-grid">
        <div>
          <span>Estado</span>
          <strong>{statusLabel(session?.status)}</strong>
        </div>
        <div>
          <span>Progreso</span>
          <strong>{progress}</strong>
        </div>
      </div>

      {confirmation && session && (
        <div className="computer-section" role="alert">
          <h3>Confirmacion requerida</h3>
          <p>{confirmation.description || confirmation.reason || "Revisa la accion antes de continuar."}</p>
          <small>{[confirmation.capability, confirmation.risk_level].filter(Boolean).join(" · ") || "Accion sensible"}</small>
          <div className="computer-actions">
            <button className="primary-action" onClick={() => confirm(true)} disabled={operation !== null}>
              <Check size={14} /> Aprobar
            </button>
            <button className="danger-action" onClick={() => confirm(false)} disabled={operation !== null}>
              <X size={14} /> Rechazar
            </button>
          </div>
        </div>
      )}

      <div className="computer-section">
        <h3>Plan</h3>
        {plan.length === 0 ? <p>El plan aparecera cuando la sesion sea preparada.</p> : plan.map((step, index) => (
          <p key={step.id ?? `${step.description}-${index}`}>
            {stepStatusMarker(step.status)} {index + 1}. {step.description}
          </p>
        ))}
      </div>

      <div className="computer-section">
        <h3>Observacion</h3>
        <p>{recentObservation?.screen_summary || "Sin observacion reciente."}</p>
        <small>{formatSources(recentObservation?.used_sources)}</small>
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
            <button key={item.id} onClick={() => setSession(item)} aria-pressed={session?.id === item.id}>
              <strong>{item.goal}</strong>
              <span>{statusLabel(item.status)} · {formatDate(item.updated_at)}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function getPlanSteps(session: ComputerUseSession | null): ComputerUsePlanStep[] {
  if (!session) return [];
  const statePlan = session.state.plan;
  if (statePlan && typeof statePlan === "object" && Array.isArray(statePlan.steps)) return statePlan.steps;
  if (Array.isArray(session.state.steps)) return session.state.steps;
  for (const action of session.actions) {
    if (action.plan?.steps) return action.plan.steps;
    if (action.steps) return action.steps;
  }
  return [];
}

function getPendingConfirmation(session: ComputerUseSession | null): ComputerUseConfirmation | null {
  if (!session || session.status !== "waiting_confirmation") return null;
  if (session.state.pending_confirmation) return session.state.pending_confirmation;
  if (session.state.confirmation) return session.state.confirmation;
  return findConfirmation(session.actions);
}

function findConfirmation(actions: ComputerUseAction[]) {
  for (let index = actions.length - 1; index >= 0; index -= 1) {
    const confirmation = actions[index].confirmation;
    if (confirmation) return confirmation;
  }
  return null;
}

function getProgress(session: ComputerUseSession | null, plan: ComputerUsePlanStep[]) {
  if (!session) return "Sin sesion";
  if (plan.length) {
    const completed = plan.filter((step) => step.status === "completed" || step.status === "skipped").length;
    return `${completed}/${plan.length} pasos`;
  }
  const iteration = typeof session.state.iteration === "number" ? session.state.iteration + 1 : session.observations.length;
  const maximum = typeof session.state.max_iterations === "number" ? `/${session.state.max_iterations}` : "";
  return iteration ? `Iteracion ${iteration}${maximum}` : statusLabel(session.status);
}

function summarizeLastAction(session: ComputerUseSession | null) {
  const last = session?.actions.at(-1);
  if (!last) return "";
  if (last.verification) return last.verification.reason ?? (last.verification.ok ? "Resultado verificado." : "La verificacion necesita revision.");
  if (last.execution) return last.execution.ok ? "Ejecucion completada." : executionError(last) || "La ejecucion necesita revision.";
  return "Accion registrada.";
}

function executionError(action: ComputerUseAction) {
  return action.execution?.results?.find((result) => result.error)?.error;
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    created: "Preparando",
    running: "En curso",
    waiting_confirmation: "Esperando confirmacion",
    completed: "Completada",
    failed: "Fallida",
    aborted: "Interrumpida",
    cancelled: "Cancelada",
  };
  return status ? labels[status] ?? status : "Inactiva";
}

function stepStatusMarker(status?: string) {
  if (status === "completed") return "[ok]";
  if (status === "running") return "[...]";
  if (status === "failed") return "[error]";
  if (status === "skipped") return "[-]";
  return "[ ]";
}

function formatSources(sources?: string[]) {
  return sources?.length ? `Fuentes: ${sources.join(", ")}` : "Fuentes: WindowManager";
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "fecha desconocida" : date.toLocaleString();
}

function errorMessage(error: unknown) {
  if (!(error instanceof Error)) return String(error);
  try {
    const parsed = JSON.parse(error.message) as { detail?: string };
    return parsed.detail ?? error.message;
  } catch {
    return error.message;
  }
}
