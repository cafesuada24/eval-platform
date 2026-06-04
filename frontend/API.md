# EvalPlatform Backend API Documentation

**Version:** 0.1.0

> **System Prompt for Frontend Agents:** You are reading the API contract for the EvalPlatform backend. Your goal is to wire frontend UI components to these endpoints. Read the **Core Data Schemas** carefully to generate TypeScript types, and follow the **Integration Workflows** to manage React state correctly.

---

## 1. Architectural Context for Frontend Agents

- **Base URL:** Assume the API is mounted at `/` or `/api` depending on your proxy setup.
- **Payload Structure:** FastAPI does **not** wrap responses in a `{ "data": ... }` envelope. Endpoints return the JSON array or object directly.
- **Validation Errors:** All endpoints will return a `422 Unprocessable Entity` if the JSON payload does not strictly match the schemas below. The error shape is the standard Pydantic `HTTPValidationError`.

---

## 2. Core Data Schemas (TypeScript Interfaces)

Generate your frontend types using these exact interfaces:

### Metric & Pipeline Configurations
```typescript
interface Metric {
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

interface Pipeline {
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
```

### Agentic Chat
```typescript
interface ChatMessage {
  role: "model" | "user" | "tool";
  content: string;
  runtime_id?: string; // UUID of the runtime trace if role is "model"
}

interface ChatRequest {
  metric_id?: string | null; // UUID format, null if it's a new unsaved session
  messages: ChatMessage[];
}

interface MetricDraft {
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

interface SaveSessionRequest {
  messages: ChatMessage[];
}

interface MetricHelperResponse {
  response_text: string;
  runtime_id: string; // The session UUID
  metric_draft?: MetricDraft | null; // Populated when the agent drafts a metric
}

interface ChatSession {
  metric_id: string; // Actually acts as the session ID
  messages: ChatMessage[];
}
```

### Documents & Generic
```typescript
interface UploadedFileMetadata {
  id: string;
  name: string;
  text: string;
  size: number;
}

interface HTTPValidationError {
  detail: Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}
```

### Datasets & Batch Processing
```typescript
interface TestCase {
  id: string; // UUID
  input_text: string;
  input_files: string[];
  expected_output?: string | null;
  metadata: Record<string, any>;
}

interface Dataset {
  id: string; // UUID
  name: string;
  cases: TestCase[];
}

interface BatchRunResult {
  job_id: string; // UUID
  pipeline_id: string; // UUID
  dataset_id: string; // UUID
  status: "PENDING" | "COMPLETED" | "FAILED";
  pipeline_run_results: any[]; 
}
```

---

## 3. Integration Workflows (Implementation Guides)

### Workflow A: The AI Metric Builder (Chat)
When building the chat interface for the AI Metric Builder, follow this state flow:
1. **Frontend State:** Maintain a `messages: ChatMessage[]` array in your local UI state.
2. **Send Message:** When the user types a message, append `{ role: "user", content: text }` to local state.
3. **API Call:** Send the *entire* `messages` array via `POST /v1/agent/chat`. 
   - *Note:* If creating a brand new metric, omit `metric_id` or set it to `null`. If editing an existing metric, pass the `metric_id`.
4. **Handle Response:** 
   - Append the returned `response_text` to the local state as a `model` message.
   - If the response includes a `metric_draft`, the AI has finalized the metric design. **You must immediately present a UI (like a modal or a side panel) allowing the user to review the `MetricDraft` and hit "Save".**
5. **Save the Draft:** When the user clicks "Save", map the `MetricDraft` into the full `Metric` schema and call `POST /v1/configs/metrics` to officially create it.
6. **Save the Session:** Immediately after `POST /configs/metrics` successfully returns the new Metric (which includes its new UUID), call `POST /v1/agent/sessions/{new_metric_id}` and pass the entire `messages` array in the body. This links your brainstorm session to the newly created metric so it can be rehydrated later!

### Workflow B: Document Knowledge Base
1. **Upload:** Use `POST /v1/documents/upload` with a `multipart/form-data` payload containing the `file`. Show a loading spinner, as the backend will synchronously extract text and embed it into ChromaDB.
2. **Refresh List:** On success, call `GET /v1/documents` to update the UI table of uploaded files.
3. *Note:* You do not need to pass document IDs to the chat endpoint. The backend automatically injects the global list of documents into the agent's prompt context.

---

## 4. REST Endpoints Reference

### 🤖 Agentic Building (AI Metric Helper)
- `POST /v1/agent/chat` → Generates conversational responses and metric drafts.
- `GET /v1/agent/sessions/{metric_id}` → Fetches past chat history for an existing metric to hydrate your local state on load.
- `POST /v1/agent/sessions/{metric_id}` → Explicitly save a chat session (e.g. immediately after creating a new metric).
- `DELETE /v1/agent/sessions/{metric_id}` → Clears the history.

### 📊 Metric Configurations
- `GET /v1/configs/metrics` → List all metrics (Use this to populate dropdowns or tables).
- `POST /v1/configs/metrics` → Create a new Metric.
- `GET /v1/configs/metrics/{metric_id}` → Get details for a specific Metric.
- `PUT /v1/configs/metrics/{metric_id}` → Update an existing Metric.

### 🔗 Pipeline Configurations
- `GET /v1/configs/pipelines` → List all pipelines.
- `POST /v1/configs/pipelines` → Create a Pipeline (attach existing metrics).
- `GET /v1/configs/pipelines/{pipeline_id}` → Get Pipeline details.
- `PUT /v1/configs/pipelines/{pipeline_id}` → Update Pipeline.

### 🔄 Client-Driven Evaluations
- `POST /v1/evaluations` → Starts a new evaluation job. Body: `{ "pipeline_id": "uuid", "dataset_id": "uuid" }`. Returns: `{ "evaluation_id": "uuid" }`.
- `POST /v1/evaluations/{evaluation_id}/testcases/{testcase_id}/submit` → Evaluates a specific test case using execution telemetry. Body: `{ "runtime_ids": ["uuid"] }`.
- `POST /v1/evaluations/{evaluation_id}/complete` → Marks the evaluation job as complete.
- `GET /v1/evaluations/{evaluation_id}` → Retrieves the `BatchRunResult` (job status and testcase pipeline run results).

### 📦 Datasets & Batch Evaluation
- `POST /v1/datasets/` → Upload a dataset (JSON or CSV). (FormData: `file`).
- `GET /v1/datasets/` → List all parsed datasets.

### 📄 Document Knowledge Base (RAG)
- `POST /v1/documents/upload` → Upload a file (txt, pdf, image) and embed it. (FormData: `file`).
- `GET /v1/documents` → List all uploaded file metadata.
- `DELETE /v1/documents/{file_id}` → Delete file and vector embeddings.

### ⚡ Runtime & Execution
- `POST /v1/events` → Ingest a batch of `RuntimeEvent` traces (returns 202).
- `GET /v1/runtimes` → List all `RuntimeState` objects.
- `GET /v1/runtimes/{runtime_id}` → Get a specific `RuntimeState`.
- `GET /v1/runtimes/{runtime_id}/variables` → Run extractors on a trace. Pass `?keys=input_text,retrieved_context` to filter.
- `DELETE /v1/runtimes/{runtime_id}` → Delete a specific `RuntimeState`.
- `POST /v1/evaluations/metrics/{metric_id}/run/{runtime_id}` → Forcibly trigger a pipeline/metric evaluation on a historical trace.
