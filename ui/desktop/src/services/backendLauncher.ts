/** Describe si la UI esta gestionando el arranque del backend o solo espera un proceso externo. */
export async function backendLauncherStatus() {
  return {
    managedByTauri: import.meta.env.PROD,
    command: import.meta.env.PROD ? "sidecar:ia-local-agent-api" : "python -m src.api.main",
  };
}
