# Implementation Report: Domain Interfaces, Repositories, YAML Schema & CRUD APIs

> Scope: Domain interface definitions · File-based repository implementations · MVP YAML schema · CRUD endpoints for eval, agent, and documents.

---

## 1. Domain Interfaces (Ports)

### What's defined

| Port | Location | Methods |
|------|----------|---------|
| `MetricRepository` | `core/eval_engine/ports.py` | `find_by_id`, `get_by_id`, `find_by_name`, `get_by_name`, `list_all`, `save`, `delete` |
| `PipelineRepository` | `core/eval_engine/ports.py` | `find_by_id`, `get_by_id`, `find_by_name`, `get_by_name`, `list_all`, `save`, `delete` |
| `AIJudgeService` | `core/eval_engine/ports.py` | `evaluate(metric, prompt, building_mode)` |
| `DatasetRepository` | `core/eval_engine/ports.py` | `get_by_id`, `save`, `list_all` |
| `BatchResultRepository` | `core/eval_engine/ports.py` | `get_by_id`, `save`, `list_all` |
| `RuntimeStateRepository` | `core/kernel/ports.py` | `find_by_id`, `get_by_id`, `save`, `list_all`, `delete` |
| `ChatSessionRepository` | `core/agents/metric_helper/ports.py` | Session read/write for the Metric Agent |

### Design notes

- **`AIJudgeService` is async**: The judge port has `async def evaluate(...)` — enforcing that all implementations must be non-blocking. This was a deliberate choice since LLM calls are I/O-bound.

---

## 2. File-Based Repository Implementations

All repositories live in `infra/repositories/` and implement the ports above using the local filesystem.

### Storage strategy

| Repository | Format | Storage key |
|------------|--------|------------|
| `YamlMetricRepository` | YAML | `fixtures/metrics/{uuid}.yaml` |
| `YamlPipelineRepository` | YAML | `fixtures/pipelines/{uuid}.yaml` |
| `YamlRuntimeStateRepository` | YAML | `fixtures/runtimes/{uuid}.yaml` |
| `JsonChatSessionRepository` | JSON | `fixtures/sessions/{uuid}.json` |
| `JsonDatasetRepository` | JSON | `fixtures/datasets/{uuid}.json` |
| `JsonBatchResultRepository` | JSON | `fixtures/batch_results/{uuid}.json` |

### Implementation pattern (consistent across all)

All YAML repositories follow this pattern:

```
__init__     → mkdir(parents=True, exist_ok=True)  # auto-create fixture dir
find_by_id   → read {id}.yaml, validate with Pydantic TypeAdapter, return None on miss
get_by_id    → find_by_id + raise DomainError on None
find_by_name → glob *.yaml, scan each file for matching name field
list_all     → glob *.yaml, deserialise all, skip malformed files with a warning log
save         → dump Pydantic model via adapter.dump_python(mode='json'), write YAML
delete       → Path.unlink() if file exists
```

### Key implementation decisions

- **`TypeAdapter` for dataclasses**: The domain models are Python `@dataclass`, not Pydantic `BaseModel`. `TypeAdapter` bridges this gap — it handles validation and serialisation without requiring domain model changes.
- **`mode='json'` on dump**: Ensures UUIDs are serialised as strings, enums as their values, and `None` fields are excluded — producing clean, human-readable YAML.
- **UUID as filename**: The filename is the entity ID. No index file needed; listing is a directory glob. Simple, but requires a full scan for `find_by_name`.
- **Graceful degradation on read**: Malformed YAML files log a warning and are skipped — the system stays operational even if one fixture is corrupted.

---

## 3. MVP YAML Schema

YAML is the canonical format for **Metrics** and **Pipelines**. The schema is finalised and in production use.

### Metric YAML Schema

Two metric types are supported: `ai-judge` (LLM scores the output) and `primitive` (formula-based).

**`ai-judge` with inline prompt template:**
```yaml
name: hallucination_index
type: ai-judge
description: "Evaluates whether the response contains hallucinations."
model_configuration:
  provider: openai
  model: gpt-4o
  temperature: 0.1
required_inputs:
  - retrieved_context
  - generated_response
prompt_template: |
  Context: {{retrieved_context}}
  Response: {{generated_response}}
  Score 0–1 where 1 = full hallucination.
scoring_scale:
  min: 0.0
  max: 1.0
  data_type: float
```

**`ai-judge` with named evaluation strategy (no inline prompt):**
```yaml
name: faithfulness_rigorous
type: ai-judge
description: "Multi-call claim verification."
evaluation_strategy: faithfulness_rigorous
model_configuration:
  provider: openai
  model: gpt-4o
  temperature: 0.0
required_inputs:
  - retrieved_context
  - output_text
scoring_scale:
  min: 0.0
  max: 1.0
  data_type: float
```

### Schema fields reference

| Field | Required | Notes |
|-------|----------|-------|
| `name` | ✅ | Unique human-readable identifier |
| `type` | ✅ | `ai-judge` or `primitive` |
| `description` | ✅ | Agent reads this to understand what the metric does |
| `required_inputs` | ✅ | Variable names the Extractor Registry must resolve |
| `scoring_scale` | ✅ | `min`, `max`, `data_type` (`float` or `integer`) |
| `model_configuration` | `ai-judge` only | `provider`, `model`, `temperature` |
| `prompt_template` | `ai-judge` optional | Jinja2 template; omit when using `evaluation_strategy` |
| `evaluation_strategy` | `ai-judge` optional | Named strategy for multi-step evaluators |
| `formula` | `primitive` only | Python expression string |
| `is_system_default` | optional | Set by the seeder; locks the metric from user deletion |

### Default metrics seeded at startup

10 system defaults are seeded from `fixtures/default_metrics/` on app startup:

| Metric | Type | Strategy |
|--------|------|---------|
| `answer_relevancy_lite` | ai-judge | inline prompt |
| `answer_relevancy_rigorous` | ai-judge | named strategy |
| `context_recall_lite` | ai-judge | inline prompt |
| `context_recall_rigorous` | ai-judge | named strategy |
| `context_relevance` | ai-judge | inline prompt |
| `faithfulness_lite` | ai-judge | inline prompt |
| `faithfulness_rigorous` | ai-judge | named strategy |
| `hallucination_index` | ai-judge | inline prompt |
| `image_caption_quality` | ai-judge | inline prompt |
| `ocr_accuracy` | ai-judge | inline prompt |

---

## 4. CRUD API Endpoints

All endpoints are versioned under `/v1`. The router is assembled in `api/v1/router.py`.

### 4a. Eval (Metrics & Pipelines) — `GET /v1/configs/...`

Full CRUD for both Metric and Pipeline configs. Metric deletion also cascades to the agent's chat session.

| Method | Path | Action |
|--------|------|--------|
| `GET` | `/v1/configs/metrics` | List all metrics |
| `GET` | `/v1/configs/metrics/{id}` | Get single metric |
| `POST` | `/v1/configs/metrics` | Create metric |
| `PUT` | `/v1/configs/metrics/{id}` | Update metric (full replace) |
| `DELETE` | `/v1/configs/metrics/{id}` | Delete metric + its agent session |
| `GET` | `/v1/configs/pipelines` | List all pipelines |
| `GET` | `/v1/configs/pipelines/{id}` | Get single pipeline |
| `POST` | `/v1/configs/pipelines` | Create pipeline (validates metric IDs exist) |
| `PUT` | `/v1/configs/pipelines/{id}` | Update pipeline (validates metric IDs exist) |
| `DELETE` | `/v1/configs/pipelines/{id}` | Delete pipeline |

**Evaluation execution** — separate from CRUD, under `/v1/evaluations/`:

| Method | Path | Action |
|--------|------|--------|
| `POST` | `/v1/evaluations` | Create a batch evaluation job |
| `POST` | `/v1/evaluations/{id}/testcases/{tc_id}/submit` | Submit a single testcase for evaluation |
| `POST` | `/v1/evaluations/{id}/complete` | Mark job as complete |
| `GET` | `/v1/evaluations` | List all jobs (paginated) |
| `GET` | `/v1/evaluations/{id}` | Get job status & results |
| `GET` | `/v1/evaluations/{id}/summary` | Aggregated metric statistics |
| `POST` | `/v1/metrics/{id}/run/{runtime_id}` | Ad-hoc single metric run against a saved runtime |

### 4b. Agent — `GET /v1/agent/...`

Manages the Metric Helper Agent's chat session and exposes the conversational chat endpoint.

| Method | Path | Action |
|--------|------|--------|
| `GET` | `/v1/agent/sessions/{metric_id}` | Retrieve session history for a metric |
| `POST` | `/v1/agent/sessions/{metric_id}` | Persist a session (on metric save) |
| `DELETE` | `/v1/agent/sessions/{metric_id}` | Clear session history |
| `POST` | `/v1/agent/chat` | Send a message to the Metric Helper Agent |

### 4c. Documents — `GET /v1/documents/...`

Handles file uploads with Gemini-powered text extraction for PDF and images.

| Method | Path | Action |
|--------|------|--------|
| `POST` | `/v1/documents/upload` | Upload file → extract text → save + index in ChromaDB |
| `GET` | `/v1/documents` | List all uploaded documents |
| `DELETE` | `/v1/documents/{file_id}` | Delete document from disk + vector store |

**Supported file types for upload:**
- Plain text (`.txt`, `.md`, `.json`, `.csv`, `.yaml`)
- PDF → Gemini OCR extraction
- Images (`.png`, `.jpg`, `.jpeg`, `.webp`) → Gemini vision extraction

---

## 5. Status Summary

| Area | Status | Notes |
|------|--------|-------|
| Domain interfaces (ports) | ✅ Complete | All 6 repositories + 1 service port defined |
| File-based repositories | ✅ Complete | 6 implementations, consistent pattern |
| MVP YAML schema (Metric) | ✅ Finalised | Two types: `ai-judge` (inline / strategy) + `primitive` |
| MVP YAML schema (Pipeline) | ✅ Finalised | References metrics by UUID with optional thresholds |
| CRUD: Metrics & Pipelines | ✅ Complete | Full CRUD + cascade delete |
| CRUD: Evaluations | ✅ Complete | Job lifecycle + per-testcase submission |
| CRUD: Agent sessions | ✅ Complete | Session read/write/delete + chat endpoint |
| CRUD: Documents | ✅ Complete | Upload (text/PDF/image), list, delete |
