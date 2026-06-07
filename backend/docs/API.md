# 🏗️ EvalPlatform Backend API Documentation

**Version:** 0.1.0  
**Base URL:** `/v1` (e.g., `http://localhost:8000/v1`)

This document serves as the complete, canonical API reference for the EvalPlatform backend. It outlines the exact data contracts, request/response payload schemas, TypeScript types, validation constraints, and integration workflows.

---

## 🧭 Table of Contents
1. [General API Concepts](#1-general-api-concepts)
2. [🤖 Agentic Helper (AI Metric Builder)](#2-agentic-helper-ai-metric-builder)
3. [📊 Metric Configurations](#3-metric-configurations)
4. [🔗 Pipeline Configurations](#4-pipeline-configurations)
5. [📦 Datasets & Test Cases](#5-datasets--test-cases)
6. [📄 Documents (RAG Knowledge Base)](#6-documents-rag-knowledge-base)
7. [⚡ Runtimes (Traces & Ingestion)](#7-runtimes-traces--ingestion)
8. [🧪 Evaluation Jobs & Orchestrator](#8-evaluation-jobs--orchestrator)
9. [❌ Global Error Schemas](#9-global-error-schemas)

---

## 1. General API Concepts

- **HEXAGONAL BOUNDARIES**: All entities follow strict domain validation. Any invalid state will be rejected at the API controller before execution.
- **REST CONTRACT**: Standard JSON envelopes. Response envelopes do not wrap data under a `data` key (e.g., arrays are returned directly as JSON arrays).
- **DATETIME FORMAT**: All timestamps are formatted as ISO 8601 UTC strings (`YYYY-MM-DDTHH:MM:SSZ`).
- **UID FORMAT**: All identifiers are standard `UUIDv4` strings.

---

## 2. 🤖 Agentic Helper (AI Metric Builder)

Endpoints used to power the conversational metric creation agent.

### `POST /v1/agent/chat`
* **Purpose**: Send a conversation history to the Metric Helper Agent to get conversational suggestions or a formatted Metric draft.
* **Input Schema (`ChatRequest`)**:
  ```json
  {
    "messages": [
      {
        "role": "user",
        "content": "I want a metric to check if my bot speaks polite English."
      }
    ],
    "metric_id": null
  }
  ```
* **Output Schema (`MetricHelperResponse`)**:
  ```json
  {
    "response_text": "I've drafted a metric for politeness based on your description...",
    "runtime_id": "8c59f0f6-2679-4d64-8396-f94de43813ff",
    "metric_draft": {
      "name": "Politeness Evaluator",
      "description": "Evaluates politeness and tone of LLM outputs.",
      "prompt_template": "Rate the politeness of this output from 1 to 5: {{output_text}}",
      "required_inputs": ["output_text"],
      "scoring_scale_min": 1.0,
      "scoring_scale_max": 5.0,
      "scoring_scale_type": "integer",
      "model_name": "gemini-1.5-pro",
      "model_provider": "google",
      "model_temperature": 0.0
    }
  }
  ```

### `GET /v1/agent/sessions/{metric_id}`
* **Purpose**: Retrieve the persisted chat session history for a specific metric.
* **Output Schema (`ChatSession`)**:
  ```json
  {
    "metric_id": "3b170ecc-6436-4da2-86e3-1f0af42c7fce",
    "messages": [
      {
        "role": "user",
        "content": "Create a conciseness metric."
      },
      {
        "role": "model",
        "content": "Here is a draft...",
        "runtime_id": "2b9921ef-e7c6-43b9-a294-b2512f45cc7d"
      }
    ]
  }
  ```

### `POST /v1/agent/sessions/{metric_id}`
* **Purpose**: Explicitly save or overwrite a chat session history for a metric.
* **Input Schema (`SaveSessionRequest`)**:
  ```json
  {
    "messages": [
      {
        "role": "user",
        "content": "Polite prompt"
      }
    ]
  }
  ```
* **Output Schema**:
  ```json
  {
    "status": "success",
    "message": "Session for metric '3b170ecc-6436-4da2-86e3-1f0af42c7fce' saved."
  }
  ```

### `DELETE /v1/agent/sessions/{metric_id}`
* **Purpose**: Clear session history.
* **Output**: `{"status": "success", "message": "Session for metric '{id}' cleared."}`

---

## 3. 📊 Metric Configurations

Manage metric templates (Primitive mathematical formulas or LLM AI-Judge prompts).

### `GET /v1/configs/metrics`
* **Purpose**: List all metrics configured in the system.
* **Output**: `list[Metric]`

### `GET /v1/configs/metrics/{metric_id}`
* **Purpose**: Get a metric template by ID.
* **Output**: `Metric` (or `404 Not Found`)

### `POST /v1/configs/metrics`
* **Purpose**: Create a new Metric.
* **Input Schema (`Metric`)**:
  ```json
  {
    "id": "e932ffab-023a-4467-b50a-e2740bc43f11",
    "name": "OCR Latency Evaluator",
    "description": "Checks if OCR processing takes less than 1 second.",
    "type": "primitive",
    "required_inputs": ["ocr_latency_ms"],
    "scoring_scale": {
      "min": 0.0,
      "max": 5000.0,
      "data_type": "float"
    },
    "formula": "ocr_latency_ms"
  }
  ```
* **Output**: The created `Metric` object.

### `PUT /v1/configs/metrics/{metric_id}`
* **Purpose**: Update an existing metric configuration. ID in path must match the body.
* **Input**: `Metric`
* **Output**: `Metric`

### `DELETE /v1/configs/metrics/{metric_id}`
* **Purpose**: Delete a metric and its associated chat sessions.
* **Output**: Status code `204 No Content`.

---

## 4. 🔗 Pipeline Configurations

Pipelines group metrics together and attach assertion thresholds to them.

### `GET /v1/configs/pipelines`
* **Purpose**: List all pipelines.
* **Output**: `list[Pipeline]`

### `GET /v1/configs/pipelines/{pipeline_id}`
* **Purpose**: Get details of a specific pipeline.
* **Output**: `Pipeline`

### `POST /v1/configs/pipelines`
* **Purpose**: Create a new evaluation pipeline. Rejects if referenced metrics do not exist.
* **Input Schema (`Pipeline`)**:
  ```json
  {
    "id": "d1354bb6-3129-45be-bbff-a129efb07908",
    "name": "Production QA Pipeline",
    "metrics": [
      {
        "metric_id": "e932ffab-023a-4467-b50a-e2740bc43f11",
        "threshold": {
          "fail_over": 1000.0,
          "warning_over": 800.0
        }
      }
    ]
  }
  ```
* **Output**: The created `Pipeline` object.

### `PUT /v1/configs/pipelines/{pipeline_id}`
* **Purpose**: Update an existing pipeline.
* **Input**: `Pipeline`
* **Output**: `Pipeline`

### `DELETE /v1/configs/pipelines/{pipeline_id}`
* **Purpose**: Delete a pipeline YAML configuration.
* **Output**: Status code `204 No Content`.

---

## 5. 📦 Datasets & Test Cases

Manage test dataset JSON files consisting of test cases, input variables, and expected outputs.

### `POST /v1/datasets/upload`
* **Purpose**: Upload a new dataset from a JSON/CSV file.
* **Format**: `multipart/form-data` with `file`.
* **Output Schema (`Dataset`)**:
  ```json
  {
    "id": "f5f4bba7-1234-4567-8910-abcdefabcdef",
    "name": "upload_file_name.json",
    "cases": [
      {
        "id": "a987ef12-3456-7890-abcd-ef1234567890",
        "inputs": {
          "query": "Translate this: hello"
        },
        "expected_outputs": {
          "expected_translation": "hola"
        },
        "metadata": {}
      }
    ],
    "schema": {
      "inputs": {
        "query": "string"
      },
      "outputs": {
        "expected_translation": "string"
      }
    }
  }
  ```

### `GET /v1/datasets`
* **Purpose**: List all parsed datasets.
* **Output**: `list[Dataset]`

### `GET /v1/datasets/{dataset_id}`
* **Purpose**: Fetch details of a specific dataset by ID.
* **Output**: `Dataset`

### `POST /v1/datasets/{dataset_id}/cases`
* **Purpose**: Add a new test case to a dataset.
* **Constraint**: The `inputs` payload **MUST** contain a `'query'` key (otherwise rejects with `422`).
* **Input Schema (`TestCaseCreate`)**:
  ```json
  {
    "inputs": {
      "query": "Is this code fast?"
    },
    "expected_outputs": {},
    "metadata": {}
  }
  ```
* **Output**: `TestCase`

### `PUT /v1/datasets/{dataset_id}/cases/{case_id}`
* **Purpose**: Update an existing test case.
* **Input**: `TestCaseUpdate` (same format as `TestCaseCreate`)
* **Output**: `TestCase`

### `DELETE /v1/datasets/{dataset_id}/cases/{case_id}`
* **Purpose**: Delete a test case.
* **Output**: `{"status": "success"}`

### `POST /v1/datasets/{dataset_id}/files`
* **Purpose**: Upload a raw data file (e.g. image/PDF) that can be referenced in a test case input.
* **Format**: `multipart/form-data` with `file`.
* **Output**:
  ```json
  {
    "file_id": "f_a12b3c4d.pdf",
    "filename": "original_invoice.pdf",
    "url": "/api/v1/datasets/{dataset_id}/files/f_a12b3c4d.pdf"
  }
  ```

### `GET /v1/datasets/{dataset_id}/files/{file_id}`
* **Purpose**: Download/retrieve the raw uploaded file.
* **Output**: Binary file stream.

---

## 6. 📄 Documents (RAG Knowledge Base)

Knowledge base files that the RAG retriever references during evaluation stages.

### `POST /v1/documents/upload`
* **Purpose**: Upload a document and embed it synchronously into ChromaDB.
* **Format**: `multipart/form-data` with `file`.
* **Output Schema (`UploadedFileMetadata`)**:
  ```json
  {
    "id": "doc_f836da10.txt",
    "name": "company_guidelines.txt",
    "text": "Extracted text content here...",
    "size": 24021
  }
  ```

### `GET /v1/documents`
* **Purpose**: List all documents stored in the database.
* **Output**: `list[UploadedFileMetadata]`

### `DELETE /v1/documents/{file_id}`
* **Purpose**: Remove a document and purge its vectors from ChromaDB.
* **Output**: `{"status": "success", "message": "Document doc_f836da10.txt deleted successfully."}`

---

## 7. ⚡ Runtimes (Traces & Ingestion)

Trace events captured from running applications. Used to extract evaluation variables.

### `PUT /v1/runtimes`
* **Purpose**: Ingest a new `RuntimeState` trace turn.
* **Input Schema (`RuntimeIngestionRequest`)**:
  ```json
  {
    "runtime_id": "0b12ef32-2345-3456-4567-56789abcdef0",
    "events": [
      {
        "runtime_id": "0b12ef32-2345-3456-4567-56789abcdef0",
        "payload": {
          "event_type": "generation",
          "provider": "google",
          "model": "gemini-1.5-flash",
          "input_text": "Translate hello",
          "prompt": "<system>...</system> Translate hello",
          "output_text": "hola",
          "latency_ms": 250,
          "input_tokens": 12,
          "output_tokens": 3
        },
        "timestamp": "2026-06-05T07:15:00Z"
      }
    ],
    "usage": {
      "input_tokens": 12,
      "output_tokens": 3,
      "latency_ms": 250,
      "memory_mb": 15,
      "estimated_cost_usd": 0.00012
    },
    "metadata": {}
  }
  ```
* **Output**: `{"runtime_id": "0b12ef32-2345-3456-4567-56789abcdef0"}`

### `GET /v1/runtimes`
* **Purpose**: List all ingested runtime traces.
* **Output**: `list[RuntimeStateGetResponse]`

### `GET /v1/runtimes/{runtime_id}`
* **Purpose**: Fetch detailed trace events for a specific runtime ID.
* **Output**: `RuntimeStateGetResponse`

### `GET /v1/runtimes/{runtime_id}/variables`
* **Purpose**: Run state extractors on the trace.
* **Query Parameters**: `?keys=input_text,retrieved_context` (comma-separated variables).
* **Output**:
  ```json
  {
    "input_text": "Translate hello",
    "retrieved_context": "No relevant documents found."
  }
  ```

---

## 8. 🧪 Evaluation Jobs & Orchestrator

Triggers pipelines and aggregates scores for execution metrics.

### `POST /v1/evaluations`
* **Purpose**: Create a new offline batch evaluation job.
* **Input Schema (`CreateEvaluationRequest`)**:
  ```json
  {
    "pipeline_id": "d1354bb6-3129-45be-bbff-a129efb07908",
    "dataset_id": "f5f4bba7-1234-4567-8910-abcdefabcdef"
  }
  ```
* **Output Schema (`CreateEvaluationResponse`)**:
  ```json
  {
    "evaluation_id": "9a38f321-4b12-4c59-bf12-45eef22495cc"
  }
  ```

### `POST /v1/evaluations/{evaluation_id}/testcases/{testcase_id}/submit`
* **Purpose**: Submit execution traces/runtimes for a specific testcase under the evaluation job and return the metric scores.
* **Input Schema (`SubmitTestcaseRequest`)**:
  ```json
  {
    "runtime_ids": ["0b12ef32-2345-3456-4567-56789abcdef0"]
  }
  ```
* **Output**:
  ```json
  {
    "status": "success",
    "result": {
      "evaluation_context_id": "3127efab-123a-4ab2-bc12-fefab12345ef",
      "pipeline_id": "d1354bb6-3129-45be-bbff-a129efb07908",
      "overall_status": 0,
      "metric_results": [
        {
          "metric_id": "e932ffab-023a-4467-b50a-e2740bc43f11",
          "score": 250.0,
          "justification": "Directly extracted 'ocr_latency_ms' value: 250.0.",
          "evidence": null,
          "assertion_status": 0
        }
      ],
      "testcase_id": "a987ef12-3456-7890-abcd-ef1234567890"
    }
  }
  ```

### `POST /v1/evaluations/metrics/{metric_id}/run/{runtime_id}`
* **Purpose**: Forcibly evaluate a single metric manually on a trace runtime.
* **Query Parameters**: `building_mode=true` (optional, defaults to true).
* **Output**: `MetricRunResult`

### `GET /v1/evaluations/{evaluation_id}`
* **Purpose**: Get the overall batch run state and results.
* **Output Schema (`BatchRunResult`)**:
  ```json
  {
    "job_id": "9a38f321-4b12-4c59-bf12-45eef22495cc",
    "pipeline_id": "d1354bb6-3129-45be-bbff-a129efb07908",
    "dataset_id": "f5f4bba7-1234-4567-8910-abcdefabcdef",
    "status": "COMPLETED",
    "pipeline_run_results": [
      {
        "evaluation_context_id": "3127efab-123a-4ab2-bc12-fefab12345ef",
        "pipeline_id": "d1354bb6-3129-45be-bbff-a129efb07908",
        "overall_status": 0,
        "metric_results": [...]
      }
    ]
  }
  ```

---

## 9. ❌ Global Error Schemas

### `422 Unprocessable Entity` (FastAPI Validation Error)
Returned when payload parameter types or required keys are violated.
```json
{
  "detail": [
    {
      "loc": ["body", "inputs"],
      "msg": "inputs must contain a 'query' field",
      "type": "value_error"
    }
  ]
}
```

### `404 Not Found`
Returned when a resource (UUID) does not exist.
```json
{
  "detail": "Dataset f5f4bba7-1234-4567-8910-abcdefabcdef not found."
}
```
