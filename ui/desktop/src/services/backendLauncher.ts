export async function backendLauncherStatus() {
  return {
    managedByTauri: false,
    command: "python -m src.api.main",
  };
}
