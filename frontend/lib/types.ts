export interface Metric {
  id: string; // UUID format
  name: string;
  description: string;
  type: "ai-judge" | "primitive";
  required_inputs: string[];
  scoring_scale: {
    min: number;
    max: number;
    data_type: "float" | "integer";
  };
  model_configuration?: {
    provider: string;
    model: string;
    temperature: number; // default 0.0
  };
  prompt_template?: string;
  formula?: string;
}

export interface Pipeline {
  id: string; // UUID format
  name: string;
  metrics: Array<{
    metric_id: string; // UUID of the metric
    threshold?: {
      fail_over?: number;
      fail_below?: number;
      warning_over?: number;
      warning_below?: number;
    };
  }>;
}

export interface ChatMessage {
  id?: string;
  role: "model" | "user" | "tool";
  content: string;
  runtime_id?: string; // UUID of the runtime trace if role is "model"
  toolInvocations?: Array<{ toolCallId: string; toolName: string; result: string }>;
}

export interface ChatRequest {
  metric_id?: string | null; // UUID format, null if it's a new unsaved session
  messages: ChatMessage[];
}

export interface MetricDraft {
  name: string;
  description: string;
  prompt_template: string;
  required_inputs: string[];
  scoring_scale_min: number;
  scoring_scale_max: number;
  scoring_scale_type: "integer" | "float";
  model_name: string;
  model_provider: string;
  model_temperature: number;
}

export interface MetricHelperResponse {
  response_text: string;
  runtime_id: string; // The session UUID
  metric_draft?: MetricDraft | null; // Populated when the agent drafts a metric
}

export interface SaveSessionRequest {
  messages: ChatMessage[];
}

export interface ChatSession {
  metric_id: string; // Actually acts as the session ID
  messages: ChatMessage[];
}

export interface UploadedFileMetadata {
  id: string;
  name: string;
  text: string;
  size: number;
}

export interface HTTPValidationError {
  detail: Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}

export interface TestCase {
  id: string; // UUID
  inputs: Record<string, any>;
  expected_outputs: Record<string, any>;
  metadata: Record<string, any>;
}

export interface Dataset {
  id: string; // UUID
  name: string;
  description?: string;
  cases: TestCase[];
}

export interface BatchRunResult {
  job_id: string; // UUID
  pipeline_id: string; // UUID
  dataset_id: string; // UUID
  pipeline_name?: string;
  dataset_name?: string;
  pass_rate?: number;
  status: "PENDING" | "COMPLETED" | "FAILED";
  pipeline_run_results: any[];
  created_at?: string;
}

export interface RuntimeEvent {
  runtime_id: string;
  event_type: string;
  payload?: Record<string, any>;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ResourceUsage {
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  memory_mb: number;
  estimated_cost_usd: number;
}

export interface RuntimeState {
  runtime_id: string;
  events: RuntimeEvent[];
  usage?: ResourceUsage;
  artifacts?: any[];
  metadata?: Record<string, any>;
}
