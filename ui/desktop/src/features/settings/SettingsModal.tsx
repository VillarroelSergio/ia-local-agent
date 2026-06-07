import { FormEvent, useEffect, useState } from "react";
import type { SettingsResponse } from "../../types/api";
import { apiClient } from "../../services/apiClient";

const fields = [
  "LMSTUDIO_BASE_URL",
  "LMSTUDIO_API_KEY",
  "DEFAULT_MODEL",
  "LLM_TEMPERATURE",
  "MAX_CONTEXT_TOKENS",
  "RESERVED_RESPONSE_TOKENS",
  "TOOLS_REQUIRE_CONFIRMATION",
  "CHROMA_PATH",
  "RAG_DOCUMENTS_ROOT",
  "RAG_TOP_K",
];

/** Renderiza el modal de settings y sincroniza valores editables con el backend. */
export function SettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [values, setValues] = useState<Record<string, string | number | boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!open) return;
    apiClient
      .settings()
      .then((response) => {
        setSettings(response);
        setValues(response.values);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [open]);

  if (!open) return null;

  /** Guarda los ajustes modificados y muestra el estado de exito o error. */
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaved(false);
    setError(null);
    try {
      const response = await apiClient.patchSettings(values);
      setSettings(response);
      setValues(response.values);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <form className="modal settings-modal" onSubmit={submit}>
        <h2>Settings</h2>
        {error && <div className="error-box">{error}</div>}
        {fields.map((field) => {
          const value = values[field];
          const isBoolean = typeof value === "boolean";
          return (
            <label key={field}>
              {field}
              {isBoolean ? (
                <input
                  type="checkbox"
                  checked={Boolean(value)}
                  onChange={(event) => setValues((current) => ({ ...current, [field]: event.target.checked }))}
                />
              ) : (
                <input
                  value={String(value ?? "")}
                  type={typeof value === "number" ? "number" : "text"}
                  onChange={(event) => setValues((current) => ({ ...current, [field]: event.target.value }))}
                />
              )}
            </label>
          );
        })}
        <small>{settings?.metadata?.requires_restart ? "Los cambios aplican al reiniciar el backend." : ""}</small>
        {saved && <span className="success-copy">Guardado</span>}
        <div className="modal-actions">
          <button type="button" className="secondary-action" onClick={onClose}>
            Cerrar
          </button>
          <button type="submit" className="primary-action">
            Guardar
          </button>
        </div>
      </form>
    </div>
  );
}
