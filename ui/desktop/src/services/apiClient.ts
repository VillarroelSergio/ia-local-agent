import type {
  ActiveWindowResponse,
  BackendStatus,
  ChatResponse,
  ComputerUseObservation,
  ComputerUseSession,
  ComputerUseSessionsResponse,
  Conversation,
  ConversationMessages,
  LmStudioDiagnostics,
  SettingsResponse,
  ToolExecuteResponse,
  ToolInfo,
  WindowInfo,
} from "../types/api";

export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8765";

export function resolveApiBaseUrl(env: Record<string, string | boolean | undefined> = import.meta.env) {
  if (env.PROD) return DEFAULT_API_BASE_URL;
  return typeof env.VITE_API_BASE_URL === "string" && env.VITE_API_BASE_URL ? env.VITE_API_BASE_URL : DEFAULT_API_BASE_URL;
}

export const API_BASE_URL = resolveApiBaseUrl();
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

  /** Devuelve metadata segura de la ventana activa para el futuro overlay. */
  activeWindow(options: { excludeOwn?: boolean } = {}) {
    const query = options.excludeOwn ? "?exclude_own=true" : "";
    return this.request<ActiveWindowResponse>(`/api/system/active-window${query}`);
  }

  /** Devuelve metadata segura de una ventana por HWND. */
  windowByHandle(handle: number) {
    return this.request<ActiveWindowResponse>(`/api/system/window/${handle}`);
  }

  /** Lista ventanas visibles para seleccion manual en overlay. */
  listWindows() {
    return this.request<{ count: number; windows: WindowInfo[] }>("/api/system/windows");
  }

  /** Diagnostica la conexion local con LM Studio y el modelo configurado. */
  lmStudioDiagnostics() {
    return this.request<LmStudioDiagnostics>("/api/system/lmstudio");
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
  sendChat(message: string, conversation_id?: string, correlation_id?: string, context?: Record<string, unknown>) {
    return this.request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id, stream: false, use_tools: true, correlation_id, context }),
    });
  }

  /** Envia un mensaje por SSE y entrega cada frame recibido al callback de streaming. */
  async streamChat(
    message: string,
    conversation_id: string | undefined,
    onChunk: (chunk: Record<string, unknown>) => void,
    signal?: AbortSignal,
    context?: Record<string, unknown>,
  ) {
    const response = await fetch(`${this.baseUrl}/api/chat/stream`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-api-key": this.token },
      body: JSON.stringify({ message, conversation_id, stream: true, use_tools: true, context }),
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

  /** Obtiene estadisticas del RAG documental. */
  ragStats() {
    return this.request<Record<string, unknown>>("/api/memory/rag/stats");
  }

  /** Lista documentos indexados en el manifest RAG. */
  ragDocuments() {
    return this.request<{ available: boolean; count: number; documents: Record<string, unknown>[] }>("/api/memory/rag/documents");
  }

  /** Indexa una ruta local para RAG documental. */
  indexRag(path: string, project_id = "default", force = false) {
    return this.request<Record<string, unknown>>("/api/memory/rag/index", {
      method: "POST",
      body: JSON.stringify({ path, project_id, force }),
    });
  }

  /** Ejecuta un objetivo mediante Computer Use Runtime. */
  runComputerUse(goal: string, max_iterations = 3) {
    return this.request<ComputerUseSession>("/api/computer-use/run", {
      method: "POST",
      body: JSON.stringify({ goal, max_iterations }),
    });
  }

  /** Observa el escritorio sin OCR salvo peticion explicita. */
  observeComputerUse(include_ocr = false) {
    return this.request<ComputerUseObservation>("/api/computer-use/observe", {
      method: "POST",
      body: JSON.stringify({ include_ocr }),
    });
  }

  /** Lista sesiones recientes de Computer Use. */
  listComputerUseSessions(limit = 10) {
    return this.request<ComputerUseSessionsResponse>(`/api/computer-use/sessions?limit=${limit}`);
  }

  /** Cancela una sesion activa de Computer Use si sigue en ejecucion. */
  cancelComputerUseSession(sessionId: string) {
    return this.request<{ cancelled: boolean; session_id: string }>(`/api/computer-use/sessions/${encodeURIComponent(sessionId)}/cancel`, {
      method: "POST",
    });
  }
}

export const apiClient = new ApiClient();
