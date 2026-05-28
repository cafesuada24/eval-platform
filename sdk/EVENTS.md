# EvalPlatform Telemetry Events Spec

This document defines the schema of discrete events pushed by the SDK that are ingested and evaluated by the EvalPlatform Backend Core.

---

## 1. Core Event Schema

Every telemetry event must conform to the `RuntimeEvent` model.

| Field | Type | Description |
| :--- | :--- | :--- |
| `event_id` | `str` | A unique identifier for the event. |
| `trace_id` | `str` | The unique identifier tracking the single chat turn. |
| `event_type` | `str` | The specific discrete occurrence type (e.g., `"ocr.completed"`). |
| `timestamp` | `datetime` | UTC timestamp of when the event occurred. |
| `payload` | `dict` | Key-value data containing the specific metrics or variables. |
| `metadata` | `dict \| None` | Optional extra details (user tags, environment, etc.). |

---

## 2. Supported Ingestion Events

The backend extracts primitive metrics and pipeline variables using exactly one definite event and payload key mapping.

### `ocr.completed`
Emitted when the OCR/Image parser completes document parsing.

* **Payload Properties:**
  * `ocr_process_time_ms` (`float`): The processing time of the OCR operation in milliseconds.
  * `ocr_failed_rate` (`float`): The failure rate of the OCR parsing (as a fraction `0.0` - `1.0`).
  * `input_artifacts_ocr` (`str`): The raw text extracted from the document by the OCR engine.

* **Example Payload:**
  ```json
  {
    "ocr_process_time_ms": 1400.0,
    "ocr_failed_rate": 0.05,
    "input_artifacts_ocr": "Invoice ID: 12345\nTotal Due: $250.00"
  }
  ```

---

### `pdf.completed`
Emitted when the PDF parsing operation completes.

* **Payload Properties:**
  * `pdf_process_time_ms` (`float`): The processing time of the PDF parser in milliseconds.
  * `pdf_failed_rate` (`float`): The failure rate of the PDF parsing (as a fraction `0.0` - `1.0`).

* **Example Payload:**
  ```json
  {
    "pdf_process_time_ms": 2800.0,
    "pdf_failed_rate": 0.0
  }
  ```

---

### `retrieval.completed`
Emitted when database or vector store context retrieval completes.

* **Payload Properties:**
  * `retrieval_time_ms` (`float`): Vector db execution time in milliseconds.
  * `retrieved_context` (`str` \| `list`): The text or list of document snippets returned by retrieval.

* **Example Payload:**
  ```json
  {
    "retrieval_time_ms": 190.0,
    "retrieved_context": "FastAPI is a modern, fast (high-performance), web framework for building APIs."
  }
  ```

---

### `generation.completed`
Emitted when the large language model response generation completes.

* **Payload Properties:**
  * `latency_ms` (`float`): The total LLM response generation latency in milliseconds.

* **Example Payload:**
  ```json
  {
    "latency_ms": 1250.5
  }
  ```

---

## 3. Extraction Fallbacks
If an event of the specified `event_type` is not present in the `state.events` list, the backend automatically falls back to checking:
1. `state.resource_usage` (for numeric performance metrics: `ocr_process_time_ms`, `ocr_failed_rate`, `retrieval_time_ms`, `pdf_process_time_ms`, `pdf_failed_rate`, `latency_ms`).
2. `state.metadata` (for variables: `input_artifacts_ocr`, `retrieved_context`).
