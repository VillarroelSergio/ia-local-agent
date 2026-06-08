import { useEffect, useRef, useState } from "react";
import { Header } from "./components/Header";
import { RightPanel } from "./components/RightPanel";
import { ChatView } from "./features/chat/ChatView";
import { ConversationSidebar } from "./features/conversations/ConversationSidebar";
import { OverlayView } from "./features/overlay/OverlayView";
import { SettingsModal } from "./features/settings/SettingsModal";
import { ConfirmationModal } from "./features/tools/ConfirmationModal";
import { apiClient } from "./services/apiClient";
import { ChatSocket, connectEvents } from "./services/wsClient";
import type { BackendStatus, ChatMessage, ConfirmationPayload, Conversation, StreamingChunk, TimelineEvent } from "./types/api";

/** Convierte un fragmento de streaming del chat en un evento de timeline con marca temporal local. */
function eventFromChunk(chunk: StreamingChunk): TimelineEvent {
  return { ...chunk, timestamp: new Date().toISOString() };
}

/** Extrae una solicitud de confirmacion de tool desde un evento recibido por chat o actividad. */
function confirmationFromEvent(event: TimelineEvent, conversationId?: string): ConfirmationPayload | null {
  if (event.type !== "tool.confirmation_required") return null;
  const data = event.data ?? event.payload ?? {};
  const name = String(data.name ?? data.tool_name ?? "");
  if (!name) return null;
  return {
    tool_name: name,
    arguments: (data.arguments as Record<string, unknown>) ?? {},
    conversation_id: conversationId,
    risk_level: typeof data.risk_level === "string" ? data.risk_level : null,
    reason: typeof data.reason === "string" ? data.reason : typeof data.error === "string" ? data.error : null,
    policy_decision: typeof data.policy_decision === "string" ? data.policy_decision : null,
    source: "chat",
  };
}

/** Coordina el estado principal de la app: conversaciones, chat, eventos, settings y confirmaciones. */
export default function App() {
  const isOverlayMode = new URLSearchParams(window.location.search).get("mode") === "overlay";
  const [backend, setBackend] = useState<BackendStatus>({ connected: false });
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [confirmation, setConfirmation] = useState<ConfirmationPayload | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);
  const chatSocket = useRef<ChatSocket | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const activeIdRef = useRef<string | undefined>();

  useEffect(() => {
    activeIdRef.current = activeId;
  }, [activeId]);

  /** Inserta un evento nuevo en la actividad y abre la confirmacion si el backend la solicita. */
  function pushEvent(event: TimelineEvent) {
    setEvents((current) => [event, ...current].slice(0, 250));
    const pending = confirmationFromEvent(event, activeIdRef.current);
    if (pending) setConfirmation(pending);
  }

  /** Consulta el estado del backend y actualiza el indicador de conexion de la cabecera. */
  async function refreshBackend() {
    const status = await apiClient.backendStatus();
    setBackend(status);
    return status;
  }

  /** Da margen al sidecar empaquetado para arrancar antes de mostrar un fallo definitivo. */
  async function waitForBackendReady(timeoutMs = 20000) {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      const status = await refreshBackend();
      if (status.connected) return true;
      setBackend({ connected: false, error: "Arrancando backend local..." });
      await new Promise((resolve) => window.setTimeout(resolve, 800));
    }
    await refreshBackend();
    return false;
  }

  /** Recarga la lista de conversaciones y selecciona la conversacion indicada o la activa. */
  async function refreshConversations(selectId?: string) {
    setLoadingConversations(true);
    try {
      const items = await apiClient.listConversations();
      setConversations(items);
      const nextId = selectId ?? activeIdRef.current ?? items[0]?.id;
      if (nextId) await selectConversation(nextId);
    } finally {
      setLoadingConversations(false);
    }
  }

  /** Cambia la conversacion activa y carga sus mensajes desde la API. */
  async function selectConversation(id: string) {
    setActiveId(id);
    const response = await apiClient.getMessages(id);
    setMessages(response.items);
  }

  useEffect(() => {
    let eventSocket: WebSocket | undefined;
    let cancelled = false;
    waitForBackendReady().then((ready) => {
      if (cancelled || !ready) return;
      refreshConversations();
      eventSocket = connectEvents(pushEvent, () => pushEvent({ type: "events.disconnected", timestamp: new Date().toISOString() }));
    });
    const interval = window.setInterval(refreshBackend, 10000);
    return () => {
      cancelled = true;
      eventSocket?.close();
      window.clearInterval(interval);
    };
  }, []);

  /** Procesa cada fragmento de respuesta en streaming y sincroniza mensajes, eventos y estado busy. */
  function handleChunk(chunk: StreamingChunk) {
    pushEvent(eventFromChunk(chunk));
    if (chunk.request_id) setRequestId(chunk.request_id);
    if (chunk.type === "message.delta" && chunk.delta) {
      setMessages((current) => {
        const copy = [...current];
        const last = copy[copy.length - 1];
        if (last?.role === "assistant" && last.metadata?.streaming) {
          copy[copy.length - 1] = { ...last, content: `${last.content ?? ""}${chunk.delta}` };
        } else {
          copy.push({ role: "assistant", content: chunk.delta, metadata: { streaming: true } });
        }
        return copy;
      });
    }
    if (chunk.type === "message.completed") {
      setBusy(false);
      setRequestId(null);
      refreshConversations(activeIdRef.current);
    }
    if (chunk.type === "error") setBusy(false);
  }

  /** Envia un mensaje usando WebSocket cuando es posible y cae a streaming HTTP o POST normal como respaldo. */
  async function sendMessage(text: string) {
    const conversation = activeId ? { id: activeId } : await apiClient.createConversation("Nueva conversacion");
    if (!activeId) {
      setActiveId(conversation.id);
      await refreshConversations(conversation.id);
    }
    setMessages((current) => [...current, { role: "user", content: text }, { role: "assistant", content: "", metadata: { streaming: true } }]);
    setBusy(true);
    try {
      const socket = new ChatSocket();
      chatSocket.current = socket;
      socket.connect(handleChunk, () => {
        if (busy) pushEvent({ type: "chat.websocket.closed", timestamp: new Date().toISOString() });
      });
      await socket.waitOpen();
      socket.send({ type: "message", message: text, conversation_id: conversation.id });
    } catch {
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        await apiClient.streamChat(text, conversation.id, (chunk) => handleChunk(chunk as unknown as StreamingChunk), controller.signal);
      } catch {
        const response = await apiClient.sendChat(text, conversation.id);
        setMessages((current) => [...current.filter((msg) => !msg.metadata?.streaming), response.message]);
        pushEvent({ type: "message.completed", data: response as unknown as Record<string, unknown>, timestamp: new Date().toISOString() });
      } finally {
        setBusy(false);
        setRequestId(null);
      }
    }
  }

  /** Cancela la respuesta activa tanto por WebSocket como por AbortController HTTP. */
  function cancel() {
    chatSocket.current?.cancel(requestId);
    abortRef.current?.abort();
    setBusy(false);
  }

  /** Responde a una confirmacion pendiente de tool y registra el resultado en la actividad. */
  async function confirmTool(approved: boolean) {
    if (!confirmation) return;
    setConfirming(true);
    try {
      const response = await apiClient.confirmTool(confirmation.tool_name, confirmation.arguments, approved, confirmation.conversation_id);
      pushEvent({ type: approved ? "tool.confirmed" : "tool.rejected", data: response as Record<string, unknown>, timestamp: new Date().toISOString() });
      setConfirmation(null);
    } finally {
      setConfirming(false);
    }
  }

  if (isOverlayMode) {
    return (
      <>
        <OverlayView messages={messages} busy={busy} activeConversationId={activeId} onSend={sendMessage} onCancel={cancel} />
        <ConfirmationModal payload={confirmation} busy={confirming} onConfirm={() => confirmTool(true)} onReject={() => confirmTool(false)} />
      </>
    );
  }

  return (
    <div className="app-frame">
      <Header backend={backend} onRetry={refreshBackend} onSettings={() => setSettingsOpen(true)} />
      <div className="main-layout">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeId}
          loading={loadingConversations}
          onNew={async () => {
            const created = await apiClient.createConversation("Nueva conversacion");
            await refreshConversations(created.id);
          }}
          onSelect={selectConversation}
          onRename={async (id, title) => {
            await apiClient.renameConversation(id, title);
            await refreshConversations(id);
          }}
          onDelete={async (id) => {
            await apiClient.deleteConversation(id);
            setMessages([]);
            setActiveId(undefined);
            await refreshConversations();
          }}
        />
        <ChatView messages={messages} busy={busy} activeConversationId={activeId} onSend={sendMessage} onCancel={cancel} />
        <RightPanel
          conversationId={activeId}
          events={events}
          onEvent={(event) => pushEvent(event as unknown as TimelineEvent)}
          onConfirmation={setConfirmation}
        />
      </div>
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <ConfirmationModal payload={confirmation} busy={confirming} onConfirm={() => confirmTool(true)} onReject={() => confirmTool(false)} />
    </div>
  );
}
