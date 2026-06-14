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

export interface ActiveWindowResponse {
  available: boolean;
  allowed: boolean;
  reason: string;
  window: {
    handle?: number | null;
    title?: string | null;
    process_name?: string | null;
    pid?: number | null;
    state?: string | null;
    monitor_index?: number | null;
    sensitive?: boolean;
  } | null;
}

export interface WindowInfo {
  handle?: number | null;
  title?: string | null;
  process_name?: string | null;
  pid?: number | null;
  state?: string | null;
  monitor_index?: number | null;
  sensitive?: boolean;
  rect?: Record<string, number> | null;
}

export interface LmStudioDiagnostics {
  ok: boolean;
  base_url: string;
  configured_model: string;
  models_url: string;
  models: string[];
  model_found: boolean;
  error?: string | null;
  last_provider_metrics?: Record<string, unknown> | null;
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

export type ComputerUseStatus =
  | "created"
  | "running"
  | "waiting_confirmation"
  | "completed"
  | "failed"
  | "aborted"
  | "cancelled"
  | string;

export interface ComputerUsePlanStep {
  id?: string;
  capability?: string;
  description: string;
  status?: "pending" | "running" | "completed" | "failed" | "skipped" | string;
  requires_confirmation?: boolean;
}

export interface ComputerUseExecutionResult {
  ok?: boolean;
  step_id?: string;
  error?: string;
  result?: Record<string, unknown>;
  policy?: {
    allowed?: boolean;
    reason?: string;
    requires_confirmation?: boolean;
  };
}

export interface ComputerUseAction {
  plan_id?: string;
  plan?: {
    id?: string;
    steps?: ComputerUsePlanStep[];
  };
  steps?: ComputerUsePlanStep[];
  execution?: {
    ok?: boolean;
    results?: ComputerUseExecutionResult[];
  };
  verification?: {
    ok?: boolean;
    reason?: string;
  };
  confirmation?: ComputerUseConfirmation;
}

export interface ComputerUseConfirmation {
  id?: string;
  step_id?: string;
  capability?: string;
  description?: string;
  reason?: string;
  risk_level?: string;
  arguments?: Record<string, unknown>;
}

export interface ComputerUseSession {
  id: string;
  goal: string;
  status: ComputerUseStatus;
  state: Record<string, unknown> & {
    iteration?: number;
    max_iterations?: number;
    plan?: string | { id?: string; steps?: ComputerUsePlanStep[] };
    steps?: ComputerUsePlanStep[];
    confirmation?: ComputerUseConfirmation;
    pending_confirmation?: ComputerUseConfirmation;
  };
  observations: ComputerUseObservation[];
  actions: ComputerUseAction[];
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  error?: string | null;
}

export interface ComputerUseSessionsResponse {
  sessions: ComputerUseSession[];
}

export interface ComputerUseObservation {
  active_window?: Record<string, unknown> | null;
  open_windows?: Record<string, unknown>[];
  controls?: Record<string, unknown>[];
  visible_text?: string;
  screen_summary?: string;
  source_order?: string[];
  used_sources?: string[];
  timestamp?: string;
  metadata?: Record<string, unknown>;
}

export interface ComputerUseConfirmationResponse {
  approved: boolean;
  session_id: string;
  session?: ComputerUseSession;
}
