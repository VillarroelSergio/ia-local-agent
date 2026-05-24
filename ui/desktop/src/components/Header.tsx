import { RefreshCw, Settings } from "lucide-react";
import type { BackendStatus } from "../types/api";

interface Props {
  backend: BackendStatus;
  onRetry: () => void;
  onSettings: () => void;
}

/** Renderiza la cabecera con estado del backend, proveedor/modelo y acciones globales. */
export function Header({ backend, onRetry, onSettings }: Props) {
  const status = backend.status ?? {};
  const provider = String(status.provider ?? "provider?");
  const model = String(status.model ?? "modelo?");
  const memory = status.memory ? "Memoria activa" : "Memoria sin datos";
  const label = backend.connected ? "Backend conectado" : backend.error === "Arrancando backend local..." ? "Conectando backend" : "Backend caido";

  return (
    <header className="app-header">
      <div className="status-group">
        <span className={`status-dot ${backend.connected ? "online" : "offline"}`} />
        <strong title={backend.error}>{label}</strong>
        <span>{provider}</span>
        <span>{model}</span>
        <span>{memory}</span>
      </div>
      <div className="header-actions">
        <button className="icon-button" title="Reintentar conexion" onClick={onRetry}>
          <RefreshCw size={17} />
        </button>
        <button className="icon-button" title="Settings" onClick={onSettings}>
          <Settings size={17} />
        </button>
      </div>
    </header>
  );
}
