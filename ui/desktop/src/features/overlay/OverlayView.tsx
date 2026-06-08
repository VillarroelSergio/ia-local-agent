import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { ChatView } from "../chat/ChatView";
import { apiClient } from "../../services/apiClient";
import type { ActiveWindowResponse, ChatMessage } from "../../types/api";

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

interface Props {
  messages: ChatMessage[];
  busy: boolean;
  activeConversationId?: string;
  onSend: (message: string) => void;
  onCancel: () => void;
}

/** Vista compacta para el futuro overlay flotante sobre Windows. */
export function OverlayView({ messages, busy, activeConversationId, onSend, onCancel }: Props) {
  const [activeWindow, setActiveWindow] = useState<ActiveWindowResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  async function refreshWindow(options: { peekBehind?: boolean } = {}) {
    if (refreshing) return;
    setRefreshing(true);
    const shouldPeek = options.peekBehind && window.__TAURI_INTERNALS__;
    let appWindow: Awaited<ReturnType<typeof getTauriWindow>> | null = null;
    try {
      setError(null);
      if (shouldPeek) {
        appWindow = await getTauriWindow();
        await appWindow?.hide();
        await delay(160);
      }
      setActiveWindow(await apiClient.activeWindow({ excludeOwn: true }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (appWindow) {
        await appWindow.show();
        await appWindow.setFocus();
      }
      setRefreshing(false);
    }
  }

  useEffect(() => {
    refreshWindow({ peekBehind: true });
    let cleanup: (() => void) | undefined;
    if (window.__TAURI_INTERNALS__) {
      import("@tauri-apps/api/event")
        .then(({ listen }) => listen("overlay-opened", () => refreshWindow({ peekBehind: true })))
        .then((unlisten) => {
          cleanup = unlisten;
        })
        .catch(() => undefined);
    }
    return () => cleanup?.();
  }, []);

  const title = activeWindow?.window?.title || (activeWindow?.window?.sensitive ? "Ventana sensible" : "Sin ventana activa");
  const process = activeWindow?.window?.process_name ?? "Proceso no disponible";
  const detail = activeWindow?.window ? `${process}${activeWindow.window.state ? ` - ${activeWindow.window.state}` : ""}` : activeWindow?.reason;

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
      <ChatView messages={messages} busy={busy} activeConversationId={activeConversationId} onSend={onSend} onCancel={onCancel} />
    </div>
  );
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function getTauriWindow() {
  const { getCurrentWindow } = await import("@tauri-apps/api/window");
  return getCurrentWindow();
}
