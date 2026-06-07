import { API_BASE_URL, API_TOKEN } from "./apiClient";
import type { StreamingChunk, TimelineEvent } from "../types/api";

const wsBase = API_BASE_URL.replace(/^http/, "ws");

/** Encapsula el WebSocket de chat para enviar mensajes, cancelar peticiones y cerrar la conexion. */
export class ChatSocket {
  private socket?: WebSocket;

  /** Abre la conexion de chat y conecta los callbacks de mensajes y cierre. */
  connect(onMessage: (chunk: StreamingChunk) => void, onClose?: () => void) {
    this.socket = new WebSocket(`${wsBase}/ws/chat?token=${encodeURIComponent(API_TOKEN)}`);
    this.socket.onmessage = (event) => onMessage(JSON.parse(event.data));
    this.socket.onclose = () => onClose?.();
    return this.socket;
  }

  /** Espera hasta que el WebSocket este abierto o rechaza si supera el timeout. */
  waitOpen(timeoutMs = 1200) {
    return new Promise<void>((resolve, reject) => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }
      const started = Date.now();
      const timer = window.setInterval(() => {
        if (this.socket?.readyState === WebSocket.OPEN) {
          window.clearInterval(timer);
          resolve();
        } else if (Date.now() - started > timeoutMs) {
          window.clearInterval(timer);
          reject(new Error("WebSocket timeout"));
        }
      }, 30);
    });
  }

  /** Serializa y envia un payload por el WebSocket abierto. */
  send(payload: Record<string, unknown>) {
    if (this.socket?.readyState !== WebSocket.OPEN) throw new Error("WebSocket no conectado");
    this.socket.send(JSON.stringify(payload));
  }

  /** Pide al backend cancelar una respuesta en curso cuando existe request_id. */
  cancel(request_id?: string | null) {
    if (request_id) this.send({ type: "cancel", request_id });
  }

  /** Cierra la conexion WebSocket si esta creada. */
  close() {
    this.socket?.close();
  }
}

/** Abre el WebSocket global de eventos para alimentar el panel de actividad. */
export function connectEvents(onEvent: (event: TimelineEvent) => void, onClose?: () => void) {
  const socket = new WebSocket(`${wsBase}/ws/events?token=${encodeURIComponent(API_TOKEN)}`);
  socket.onmessage = (event) => onEvent(JSON.parse(event.data));
  socket.onclose = () => onClose?.();
  return socket;
}
