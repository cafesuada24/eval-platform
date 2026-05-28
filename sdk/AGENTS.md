# EvalPlatform: Python Telemetry SDK
> The lightweight, non-blocking telemetry capture client for integrating AI applications into the EvalPlatform ecosystem.

## 1. SDK Principles

| Principle | Technical Implication |
| :--- | :--- |
| **Zero Overhead** | Application performance must never degrade due to telemetry. Network I/O happens in background threads/tasks using batched flushes. |
| **Fail-Safe** | If the backend is down or the network drops, the SDK silently drops logs or gracefully retries without raising exceptions in the host application. |
| **Framework-Agnostic** | The SDK does not care if the host uses LangChain, LlamaIndex, or raw API calls. It expects developers to map their framework's output to the SDK's explicit data contracts. |
| **Multimodal-First** | Artifacts (images, PDFs, OCR results) are treated as first-class citizens alongside standard text inputs and outputs. |
| **Type Parity** | The SDK maintains exact Pydantic model parity with the backend to guarantee strict data contracts before serialization. |

---

## 2. Domain Lexicon

### Core Telemetry Models
* **`RuntimeEvent`**: A discrete temporal occurrence pushed by the SDK (e.g., `generation.start`, `generation.end`, `tool.call`).
* **`RuntimeState`**: The aggregated payload representing a complete interaction (Input, Output, Latency, Artifacts, Metadata). The SDK provides high-level helpers to construct this and send it as a terminal event.
* **`Artifact`**: A multimodal object attached to a trace (e.g., an extracted PDF text block, an OCR'd image, or an intermediate JSON state).

### Client Mechanisms
* **`EvalClient`**: The core singleton or instance responsible for maintaining the in-memory buffer and managing background flushes.
* **`Buffer`**: The thread-safe queue holding events before they are sent to the backend.
* **`Decorator / Context Manager`**: High-level SDK wrappers (`@capture_trace` or `with trace:`) that automatically calculate latency and package inputs/outputs into a `RuntimeState`.

---

## 3. System Architecture & Tech Stack

* **HTTP Client:** `httpx` (Supports both synchronous and asynchronous non-blocking requests).
* **Validation & Serialization:** `pydantic` (Strict type checking matching the backend).
* **Concurrency:** `asyncio` and `threading` (For background buffer flushing without blocking the main event loop).
* **Lifecycle Management:** `atexit` (To guarantee the buffer is flushed before the host process terminates).

---

## 4. SDK Directory Structure

```text
sdk/
├── pyproject.toml          # uv project dependencies
├── src/
│   └── evalplatform_sdk/
│       ├── __init__.py     # Public API exports
│       ├── client.py       # EvalClient and background worker logic
│       ├── models.py       # Pydantic data contracts (RuntimeEvent, RuntimeState)
│       └── helpers.py      # Decorators and Context Managers
```
---
