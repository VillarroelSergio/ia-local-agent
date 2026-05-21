import { API_BASE_URL, API_TOKEN } from "./apiClient";
import type { StreamingChunk, TimelineEvent } from "../types/api";

const wsBase = API_BASE_URL.replace(/^http/, "ws");

export class ChatSocket {
  private socket?: WebSocket;

  connect(onMessage: (chunk: StreamingChunk) => void, onClose?: () => void) {
    this.socket = new WebSocket(`${wsBase}/ws/chat?token=${encodeURIComponent(API_TOKEN)}`);
    this.socket.onmessage = (event) => onMessage(JSON.parse(event.data));
    this.socket.onclose = () => onClose?.();
    return this.socket;
  }

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

  send(payload: Record<string, unknown>) {
    if (this.socket?.readyState !== WebSocket.OPEN) throw new Error("WebSocket no conectado");
    this.socket.send(JSON.stringify(payload));
  }

  cancel(request_id?: string | null) {
    if (request_id) this.send({ type: "cancel", request_id });
  }

  close() {
    this.socket?.close();
  }
}

export function connectEvents(onEvent: (event: TimelineEvent) => void, onClose?: () => void) {
  const socket = new WebSocket(`${wsBase}/ws/events?token=${encodeURIComponent(API_TOKEN)}`);
  socket.onmessage = (event) => onEvent(JSON.parse(event.data));
  socket.onclose = () => onClose?.();
  return socket;
}
