export type Role = "system" | "user" | "assistant" | "tool";

export interface ChatMessage {
  id?: string | null;
  role: Role;
  content?: string | null;
  created_at?: string | null;
  metadata?: Record<string, unknown>;
  tool_calls?: Record<string, unknown>[] | null;
  tool_call_id?: string | null;
  name?: string | null;
}

export interface Conversation {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
  summary?: string | null;
  message_count: number;
}

export interface ConversationMessages {
  items: ChatMessage[];
  total: number;
  limit: number;
  offset: number;
}

export interface StreamingChunk {
  type: string;
  delta?: string | null;
  data?: Record<string, unknown>;
  request_id?: string;
  correlation_id?: string | null;
}

export interface ChatResponse {
  conversation_id: string;
  message: ChatMessage;
  metadata: {
    provider: string;
    model: string;
    request_id: string;
    correlation_id?: string | null;
  };
}

export interface ToolInfo {
  name: string;
  description: string;
  category: string;
  risk_level?: string | null;
  requires_confirmation?: boolean;
  schema: Record<string, unknown>;
}

export interface ToolExecuteResponse {
  call_id: string;
  tool_name: string;
  ok: boolean;
  result?: unknown;
  error?: Record<string, unknown> | null;
  requires_user_action?: boolean;
  risk_level?: string | null;
  duration_ms?: number;
}

export interface TimelineEvent {
  type: string;
  timestamp?: string;
  request_id?: string | null;
  correlation_id?: string | null;
  data?: Record<string, unknown>;
  payload?: Record<string, unknown>;
  delta?: string | null;
}

export interface BackendStatus {
  health?: Record<string, unknown>;
  status?: Record<string, unknown>;
  metrics?: Record<string, unknown>;
  connected: boolean;
  error?: string;
}

export interface SettingsResponse {
  values: Record<string, string | number | boolean>;
  metadata: Record<string, unknown>;
}

export interface ConfirmationPayload {
  tool_name: string;
  arguments: Record<string, unknown>;
  conversation_id?: string | null;
  risk_level?: string | null;
  reason?: string | null;
  policy_decision?: string | null;
  source?: "chat" | "tools";
}
