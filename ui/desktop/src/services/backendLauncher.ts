/** Describe si la UI esta gestionando el arranque del backend o solo espera un proceso externo. */
export async function backendLauncherStatus() {
  return {
    managedByTauri: false,
    command: "python -m src.api.main",
  };
}
