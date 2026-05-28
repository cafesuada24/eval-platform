# SDK Implementation Plan

**Objective:** Build a robust, non-blocking Python SDK that captures AI telemetry, enforces strict data contracts, and batches network requests to the EvalPlatform backend.

## Phase 1: Data Contracts & Type Parity
**Goal:** Establish the strict Pydantic schemas that mirror the backend, ensuring data is validated client-side before network transmission.

1.  **Core Models (`src/evalplatform_sdk/models.py`)**:
    * Create `Artifact` (BaseModel): 
      * `type`: str. **Crucial Standard:** Use specific types like `"application/pdf"`, `"image_ocr"`, or `"generated_image_description"` to ensure backend compatibility.
      * `content`: Any (String for OCR text, Base64 for raw images).
      * `metadata`: dict | None.
    * Create `RuntimeEvent` (BaseModel): ...
    * Create `RuntimeState` (BaseModel): ...
    ```python
    from typing import Any, Literal, Optional
    from pydantic import BaseModel

    ArtifactType = Literal[
        "document/text",        # Markdown, TXT
        "document/pdf",
        "image/ocr",            # Tesseract/Vision API results
        "image/caption",        # Descriptive image alt-text
        "generated/description" # LLM outputted image context
    ]

    class Artifact(BaseModel):
        type: ArtifactType
        content: Any
        metadata: dict[str, Any] | None = None
        
    class RuntimeState(BaseModel): ... # Core properties
    ```

---

## Phase 2: The Non-Blocking Client Engine
**Goal:** Implement the thread-safe buffer and background HTTP flushing mechanism.

1.  **Client Initialization (`src/evalplatform_sdk/client.py`)**:
    * Create the `EvalClient` class.
    * Initialize `_buffer` (List[RuntimeEvent]) and a thread-safe `Lock`.
    * Accept initialization parameters: `api_key`, `base_url`, `flush_interval_seconds` (default 3), `max_buffer_size` (default 50).
2.  **Background Worker & Flushing**:
    * Write `_flush_buffer()`: Safely extract all items from `_buffer`, clear it, and use `httpx.post` to send the payload to `{base_url}/v1/events`. Wrap in a broad `try/except` to ensure network failures never crash the host app.
    * Write `_background_loop()`: A loop that calls `_flush_buffer()` based on `flush_interval_seconds` or when `max_buffer_size` is reached.
    * Register an `atexit.register(self.flush_sync)` hook to guarantee final events are sent when the application shuts down.
3.  **Low-Level Event Ingestion**:
    * Implement `log_event(event: RuntimeEvent)`: Appends the event to the internal buffer and triggers a flush if the buffer exceeds `max_buffer_size`.

---

## Phase 3: Developer Experience (DX) & Wrappers
**Goal:** Provide high-level wrappers so developers can capture complex states with minimal boilerplate.

1.  **Context Managers (`src/evalplatform_sdk/helpers.py`)**:
    * Implement a `trace(trace_id: str = None)` context manager.
    * **Logic:** Records a `start_time` on entry. On exit, calculates `latency_ms`, builds a `RuntimeState`, and converts it into a terminal `RuntimeEvent` (e.g., `event_type="trace.completed"`).
2.  **Function Decorators**:
    * Implement `@capture_trace`.
    * **Logic:** Wraps an AI generation function. Automatically captures `kwargs` as `metadata` or `input_text`, times the execution, captures the return value as `output_text`, and sends the state to the client buffer.

---

## Phase 4: Error Handling & Resilience
**Goal:** Ensure the SDK acts as a silent observer that never degrades the host application.

1.  **Graceful Degradation (`src/evalplatform_sdk/client.py`)**:
    * Configure `httpx` timeouts (e.g., 2 seconds max for the connection pool).
    * Implement a circuit breaker or exponential backoff in `_flush_buffer` if the backend returns `5xx` errors.
    * Cap the absolute maximum buffer size (e.g., 5000 events) to prevent Out-Of-Memory (OOM) errors in the host application if the network is permanently down. If the cap is reached, new events should be silently dropped (with an optional standard library `logging.warning`)
