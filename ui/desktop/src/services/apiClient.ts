import type {
  BackendStatus,
  ChatResponse,
  Conversation,
  ConversationMessages,
  SettingsResponse,
  ToolExecuteResponse,
  ToolInfo,
} from "../types/api";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8765";
export const API_TOKEN = import.meta.env.VITE_LOCAL_API_TOKEN ?? "local-dev-token";

type RequestOptions = RequestInit & { auth?: boolean };

/** Cliente HTTP tipado para hablar con la API local del agente desde la UI. */
export class ApiClient {
  /** Guarda la URL base y el token que se usaran por defecto en todas las peticiones autenticadas. */
  constructor(private readonly baseUrl = API_BASE_URL, private readonly token = API_TOKEN) {}

  /** Ejecuta una peticion HTTP, aplica cabeceras comunes y convierte errores de backend en excepciones. */
  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const headers = new Headers(options.headers);
    if (!headers.has("content-type") && options.body) headers.set("content-type", "application/json");
    if (options.auth !== false) headers.set("x-api-key", this.token);
    const response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `${response.status} ${response.statusText}`);
    }
    return response.json() as Promise<T>;
  }

  /** Consulta el endpoint publico de salud del backend. */
  health() {
    return this.request<Record<string, unknown>>("/api/health", { auth: false });
  }

  /** Consulta el estado funcional del backend, incluyendo proveedor y modelo configurados. */
  status() {
    return this.request<Record<string, unknown>>("/api/status", { auth: false });
  }

  /** Recupera metricas basicas del backend para diagnostico de la UI. */
  metrics() {
    return this.request<Record<string, unknown>>("/api/metrics", { auth: false });
  }

  /** Combina salud, estado y metricas en un unico objeto tolerante a fallos de conexion. */
  async backendStatus(): Promise<BackendStatus> {
    try {
      const [health, status, metrics] = await Promise.all([this.health(), this.status(), this.metrics()]);
      return { connected: true, health, status, metrics };
    } catch (error) {
      return { connected: false, error: error instanceof Error ? error.message : String(error) };
    }
  }

  /** Obtiene todas las conversaciones guardadas. */
  listConversations() {
    return this.request<Conversation[]>("/api/conversations");
  }

  /** Crea una conversacion nueva con el titulo indicado. */
  createConversation(title = "Nueva conversacion") {
    return this.request<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  }

  /** Renombra una conversacion existente. */
  renameConversation(id: string, title: string) {
    return this.request<Conversation>(`/api/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
  }

  /** Borra una conversacion por identificador. */
  deleteConversation(id: string) {
    return this.request<{ deleted: string }>(`/api/conversations/${id}`, { method: "DELETE" });
  }

  /** Carga los mensajes recientes de una conversacion. */
  getMessages(id: string) {
    return this.request<ConversationMessages>(`/api/conversations/${id}/messages?limit=200`);
  }

  /** Envia un mensaje de chat sin streaming y devuelve la respuesta completa del asistente. */
  sendChat(message: string, conversation_id?: string, correlation_id?: string) {
    return this.request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id, stream: false, use_tools: true, correlation_id }),
    });
  }

  /** Envia un mensaje por SSE y entrega cada frame recibido al callback de streaming. */
  async streamChat(
    message: string,
    conversation_id: string | undefined,
    onChunk: (chunk: Record<string, unknown>) => void,
    signal?: AbortSignal,
  ) {
    const response = await fetch(`${this.baseUrl}/api/chat/stream`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-api-key": this.token },
      body: JSON.stringify({ message, conversation_id, stream: true, use_tools: true }),
      signal,
    });
    if (!response.ok || !response.body) throw new Error(await response.text());
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const dataLine = frame.split("\n").find((line) => line.startsWith("data: "));
        if (dataLine) onChunk(JSON.parse(dataLine.slice(6)));
      }
    }
  }

  /** Lista las tools disponibles para ejecucion desde la UI. */
  listTools() {
    return this.request<ToolInfo[]>("/api/tools");
  }

  /** Recupera la definicion completa de una tool por nombre. */
  getTool(name: string) {
    return this.request<ToolInfo>(`/api/tools/${encodeURIComponent(name)}`);
  }

  /** Obtiene el historial de auditoria de ejecuciones de tools. */
  toolAudit() {
    return this.request<Record<string, unknown>[]>("/api/tools/audit");
  }

  /** Solicita la ejecucion de una tool con sus argumentos y contexto de conversacion opcional. */
  executeTool(name: string, arguments_: Record<string, unknown>, conversation_id?: string, preapproved = false) {
    return this.request<ToolExecuteResponse>(`/api/tools/${encodeURIComponent(name)}/execute`, {
      method: "POST",
      body: JSON.stringify({ arguments: arguments_, conversation_id, preapproved }),
    });
  }

  /** Aprueba o rechaza una ejecucion de tool que quedo pendiente de confirmacion. */
  confirmTool(tool_name: string, arguments_: Record<string, unknown>, approved: boolean, conversation_id?: string | null) {
    return this.request<ToolExecuteResponse | { ok: false; cancelled: true }>("/api/tools/confirm", {
      method: "POST",
      body: JSON.stringify({ tool_name, arguments: arguments_, approved, conversation_id }),
    });
  }

  /** Carga los ajustes editables que expone el backend. */
  settings() {
    return this.request<SettingsResponse>("/api/settings");
  }

  /** Persiste cambios parciales en los ajustes de la aplicacion. */
  patchSettings(values: Record<string, unknown>) {
    return this.request<SettingsResponse>("/api/settings", {
      method: "PATCH",
      body: JSON.stringify({ values }),
    });
  }

  /** Obtiene estadisticas del sistema de memoria/RAG. */
  memoryStats() {
    return this.request<Record<string, unknown>>("/api/memory/stats");
  }

  /** Lanza la reconstruccion del indice de memoria/RAG. */
  rebuildMemory() {
    return this.request<Record<string, unknown>>("/api/memory/rebuild", { method: "POST" });
  }

  /** Busca entradas de memoria relacionadas con el texto indicado. */
  searchMemory(query: string) {
    return this.request<unknown[]>(`/api/memory/search?query=${encodeURIComponent(query)}`);
  }
}

export const apiClient = new ApiClient();
