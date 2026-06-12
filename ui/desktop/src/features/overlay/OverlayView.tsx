import { FileText, List, RefreshCw, ScanText } from "lucide-react";
import { useEffect, useState } from "react";
import { ChatView } from "../chat/ChatView";
import { apiClient } from "../../services/apiClient";
import type { ActiveWindowResponse, ChatMessage, WindowInfo } from "../../types/api";

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

interface Props {
  messages: ChatMessage[];
  busy: boolean;
  activeConversationId?: string;
  onSend: (message: string, context?: Record<string, unknown>) => void;
  onCancel: () => void;
}

/** Vista compacta para el futuro overlay flotante sobre Windows. */
export function OverlayView({ messages, busy, activeConversationId, onSend, onCancel }: Props) {
  const [activeWindow, setActiveWindow] = useState<ActiveWindowResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [focusKey, setFocusKey] = useState(0);
  const [windows, setWindows] = useState<WindowInfo[]>([]);
  const [showWindows, setShowWindows] = useState(false);

  async function refreshWindow(options: { peekBehind?: boolean } = {}) {
    if (refreshing) return;
    setRefreshing(true);
    try {
      setError(null);
      if (options.peekBehind && window.__TAURI_INTERNALS__) {
        const { invoke } = await import("@tauri-apps/api/core");
        await invoke("refresh_overlay_context_command");
        return;
      }
      setActiveWindow(await apiClient.activeWindow({ excludeOwn: true }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    restoreOverlayBounds().catch(() => undefined);
    refreshWindow({ peekBehind: true });
    let cleanup: (() => void) | undefined;
    if (window.__TAURI_INTERNALS__) {
      import("@tauri-apps/api/event")
        .then(({ listen }) => {
          const opened = listen("overlay-opened", () => {
            setFocusKey((value) => value + 1);
            persistOverlayBounds().catch(() => undefined);
          });
          const context = listen<{ handle: number }>("overlay-context", async (event) => {
            setFocusKey((value) => value + 1);
            if (event.payload?.handle) {
              setActiveWindow(await apiClient.windowByHandle(event.payload.handle));
            }
          });
          return Promise.all([opened, context]).then((items) => () => items.forEach((unlisten) => unlisten()));
        })
        .then((unlisten) => {
          cleanup = unlisten;
        })
        .catch(() => undefined);
    }
    window.addEventListener("beforeunload", () => persistOverlayBounds().catch(() => undefined));
    return () => cleanup?.();
  }, []);

  const title = activeWindow?.window?.title || (activeWindow?.window?.sensitive ? "Ventana sensible" : "Sin ventana activa");
  const process = activeWindow?.window?.process_name ?? "Proceso no disponible";
  const detail = activeWindow?.window ? `${process}${activeWindow.window.state ? ` - ${activeWindow.window.state}` : ""}` : activeWindow?.reason;

  function windowContext() {
    return activeWindow?.window ? { active_window: activeWindow.window } : undefined;
  }

  function useWindowAsContext() {
    const context = windowContext();
    if (!context) return;
    onSend("Usa esta ventana como contexto y dime en que puedes ayudarme.", context);
  }

  function readVisibleText() {
    const context = windowContext();
    if (!context) return;
    const ok = window.confirm("Leer texto visible requiere OCR bajo demanda sobre la ventana objetivo. Continuar?");
    if (!ok) return;
    const handle = activeWindow?.window?.handle;
    if (handle) {
      apiClient
        .executeTool("focus_window", { handle }, activeConversationId, true)
        .then(() => apiClient.executeTool("ocr_active_window", { target: "active_window", language: "spa+eng" }, activeConversationId, true))
        .then((result) => {
          const text = typeof result.result === "object" && result.result ? String((result.result as Record<string, unknown>).text ?? "") : "";
          onSend("Resume este OCR de la ventana seleccionada.", { ...context, ocr_text: text, requested_action: "ocr_visible_text" });
        })
        .catch((err) => onSend(`No pude ejecutar OCR: ${err instanceof Error ? err.message : String(err)}`, context));
      return;
    }
    onSend("Lee el texto visible de la ventana activa con OCR y resume lo importante.", { ...context, requested_action: "ocr_visible_text" });
  }

  async function loadWindows() {
    const response = await apiClient.listWindows();
    setWindows(response.windows);
    setShowWindows((value) => !value);
  }

  async function selectWindow(windowInfo: WindowInfo) {
    if (!windowInfo.handle) return;
    setActiveWindow(await apiClient.windowByHandle(windowInfo.handle));
    setShowWindows(false);
  }

  return (
    <div className="overlay-frame">
      <header className="overlay-header">
        <div className="overlay-window">
          <strong>{title}</strong>
          <span>{error ?? detail ?? "Contexto no disponible"}</span>
        </div>
        <button type="button" className="icon-button" title="Actualizar ventana activa" onClick={() => refreshWindow({ peekBehind: true })}>
          <RefreshCw size={16} />
        </button>
      </header>
      <div className="overlay-actions">
        <button type="button" className="secondary-action" onClick={loadWindows}>
          <List size={15} />
          Ventanas
        </button>
        <button type="button" className="secondary-action" onClick={useWindowAsContext} disabled={!activeWindow?.window}>
          <FileText size={15} />
          Usar ventana
        </button>
        <button type="button" className="secondary-action" onClick={readVisibleText} disabled={!activeWindow?.window}>
          <ScanText size={15} />
          Leer texto
        </button>
      </div>
      {showWindows && (
        <div className="overlay-window-list">
          {windows.map((item) => (
            <button key={`${item.handle}-${item.title}`} type="button" onClick={() => selectWindow(item)}>
              <strong>{item.title || "Sin titulo"}</strong>
              <span>{item.process_name ?? "Proceso desconocido"} {item.handle ? `#${item.handle}` : ""}</span>
            </button>
          ))}
        </div>
      )}
      <ChatView messages={messages} busy={busy} activeConversationId={activeConversationId} autoFocusKey={focusKey} onSend={onSend} onCancel={onCancel} />
    </div>
  );
}

async function getTauriWindow() {
  const { getCurrentWindow } = await import("@tauri-apps/api/window");
  return getCurrentWindow();
}

async function persistOverlayBounds() {
  if (!window.__TAURI_INTERNALS__) return;
  const appWindow = await getTauriWindow();
  const [position, size] = await Promise.all([appWindow.outerPosition(), appWindow.outerSize()]);
  localStorage.setItem("overlay.bounds", JSON.stringify({ x: position.x, y: position.y, width: size.width, height: size.height }));
}

async function restoreOverlayBounds() {
  if (!window.__TAURI_INTERNALS__) return;
  const raw = localStorage.getItem("overlay.bounds");
  if (!raw) return;
  const bounds = JSON.parse(raw) as { x: number; y: number; width: number; height: number };
  const { LogicalPosition, LogicalSize } = await import("@tauri-apps/api/dpi");
  const appWindow = await getTauriWindow();
  await appWindow.setPosition(new LogicalPosition(bounds.x, bounds.y));
  await appWindow.setSize(new LogicalSize(Math.max(360, bounds.width), Math.max(520, bounds.height)));
}
