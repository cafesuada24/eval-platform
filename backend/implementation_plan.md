# Implementation Plan: EvalPlatform Ultimate Goals Alignment

This document proposes a detailed, multi-phase implementation to address the bottlenecks identified in the Project Alignment Report. It outlines structural changes and architectural trade-offs to bring the platform to its ultimate goals.

## User Review Required
> [!IMPORTANT]
> **Batch Evaluation Architecture**
> In Phase 2, we propose using FastAPI's `BackgroundTasks` for asynchronous batch evaluation to keep the architecture simple. If you anticipate extremely large datasets (>10,000 rows per run) or need distributed workers immediately, we should pivot to a message queue like Celery/Redis. Please confirm if `BackgroundTasks` is sufficient for the initial implementation.

## Open Questions
> [!WARNING]
> **Default Metrics Mutability**
> If we seed default metrics into the database during startup (Phase 1), should users be allowed to edit these default metrics? If they edit them, it may break future platform upgrades. We could mark them as `is_system_default=True` and make them immutable. What is your preference?

---

## Phase 1: Metric Quality & Foundation (Feature 2)

**Goal:** Provide a comprehensive set of default metrics to evaluate multimodal processing capability.

**Structural Changes:**
- **[NEW]** `backend/fixtures/metrics/`
  - Add predefined YAML definitions for multimodal metrics (e.g., `ocr_accuracy.yaml`, `image_caption_quality.yaml`, `context_relevance.yaml`, `hallucination_index.yaml`).
- **[MODIFY]** `backend/app/main.py`
  - Add a startup event hook to read the YAMLs in `fixtures/metrics/` and upsert them into the `MetricRepository` if they don't already exist.

**Trade-offs:**
- *Seeding in DB vs Reading from Disk:* We will seed them into the DB. This allows the `MetricHelperAppService` and Orchestrator to treat them exactly like user-created metrics, reducing branching logic. The trade-off is handling versioning if a system metric needs an update but a user has already modified their DB copy.

---

## Phase 2: Offline Evaluation & Golden Datasets (Feature 3)

**Goal:** Ingest golden datasets and perform offline pipeline evaluation.

**Structural Changes:**
- **[MODIFY]** `backend/app/core/eval_engine/models.py`
  - Add `Dataset` and `DatasetEntry` (representing a mock `RuntimeState` or test case input).
- **[NEW]** `backend/app/core/eval_engine/ports.py` (update)
  - Add `DatasetRepository`.
- **[NEW]** `backend/app/api/v1/endpoints/datasets.py`
  - Endpoints: `POST /datasets` (upload CSV/JSON), `GET /datasets`.
- **[MODIFY]** `backend/app/api/v1/endpoints/configs.py`
  - Add endpoint: `POST /pipelines/{pipeline_id}/run_batch`.
- **[NEW]** `backend/app/core/eval_engine/services/batch_orchestrator.py`
  - A service to fan out `MetricEvaluatorService` calls asynchronously across a `Dataset`.

**Trade-offs:**
- *Async Background Tasks vs Dedicated Queue:* For simplicity and keeping the platform "Absolute Zero-Config", we will use native `asyncio.gather` and FastAPI `BackgroundTasks` for batch runs instead of introducing Redis/Celery. The trade-off is reduced fault tolerance if the backend API pod crashes mid-evaluation.

---

## Phase 3: SDK Evaluation Extensions (Feature 5)

**Goal:** Extend the Python SDK to invoke the client endpoints for running offline test cases.

**Structural Changes:**
- **[MODIFY]** `sdk/src/evalplatform_sdk/client.py`
  - Add management namespaces. Instead of just telemetry, the client will have `client.datasets` and `client.pipelines`.
- **[NEW]** `sdk/src/evalplatform_sdk/management.py`
  - Implement `DatasetClient` with `.upload_json()` and `.upload_csv()`.
  - Implement `PipelineClient` with `.evaluate_batch(dataset_id)`.

**Trade-offs:**
- *Fat SDK vs Thin Telemetry SDK:* We are making the SDK a "Fat" client that serves both runtime apps (telemetry) and CI/CD scripts (offline eval). To mitigate bloat, management HTTP calls will be strictly synchronous and separated from the background thread used for non-blocking telemetry.

---

## Phase 4: Seamless Metric Testing (Feature 1)

**Goal:** Allow users to build and test metrics seamlessly without needing a pre-existing `runtime_id`.

**Structural Changes:**
- **[MODIFY]** `backend/app/api/v1/endpoints/evals.py`
  - Add endpoint: `POST /metrics/{metric_id}/test_mock` which accepts an ephemeral `DatasetEntry` payload.
- **[MODIFY]** `backend/app/core/agents/metric_helper/services.py`
  - Allow the AI Metric Agent to propose a mock `DatasetEntry` JSON payload based on the metric it just built, so the frontend can immediately render a "Test this Metric" button.

**Trade-offs:**
- *Mock Validation:* Bypassing the actual telemetry pipeline means the mock payload might miss some implicit fields (like timestamps). We will enforce validation by running the mock payload through the exact same `RuntimeState` Pydantic models before evaluation.

---

## Verification Plan

### Automated Tests
- **Backend:** 
  - `pytest tests/core/eval_engine/test_batch_orchestrator.py`
  - `pytest tests/api/v1/test_datasets.py`
- **SDK:**
  - `pytest tests/test_management_client.py`

### Manual Verification
- Upload a JSON golden dataset via the Python SDK.
- Trigger a batch pipeline evaluation from the Python SDK.
- Observe the backend processing the batch via `BackgroundTasks` without blocking.
- Start a chat with the Metric Agent, build an OCR accuracy metric, and test it instantly using a mock payload proposed by the Agent.
