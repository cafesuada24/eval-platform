# Comprehensive LLM Retry Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure all LLM interaction paths are protected by an async exponential backoff retry loop with 5 attempts, a base delay of 1.2 seconds, and coverage for `litellm.BadRequestError`.

**Architecture:** Modify the shared `with_retry` decorator config to default to 5 attempts, 1.2s base delay, and catch `litellm.BadRequestError`. Apply this decorator to `_call_llm_structured` and the OCR `upload_file` endpoint.

**Tech Stack:** Python, FastAPI, LiteLLM, Pytest

---

### Task 1: Update Retry Decorator settings

**Files:**
- Modify: `backend/app/core/shared/retry.py`

- [ ] **Step 1: Modify defaults and catch BadRequestError**

Update `backend/app/core/shared/retry.py` to:
1. Include `litellm.BadRequestError` in `RETRYABLE_EXCEPTIONS`.
2. Change the default values of `max_attempts` to `5` and `base_delay` to `1.2`.

```python
RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    litellm.RateLimitError,
    litellm.ServiceUnavailableError,
    litellm.BadGatewayError,
    litellm.InternalServerError,
    litellm.APIConnectionError,  # also catches litellm.Timeout (subclass)
    litellm.BadRequestError,      # catches mapped quota/request errors
    genai_errors.ServerError,
    TimeoutError,
    ConnectionError,
)

def with_retry(
    max_attempts: int = 5,
    base_delay: float = 1.2,
    max_delay: float = 30.0,
    exceptions: tuple[type[BaseException], ...] = RETRYABLE_EXCEPTIONS,
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/shared/retry.py
git commit -m "feat: configure retry decorator for 5 attempts, 1.2s delay, and BadRequestError"
```

---

### Task 2: Apply Retry to Multi-Step Evaluator Calls

**Files:**
- Modify: `backend/app/core/eval_engine/services/multi_step_evaluators.py`

- [ ] **Step 1: Import with_retry and decorate _call_llm_structured**

Modify `backend/app/core/eval_engine/services/multi_step_evaluators.py` to import `with_retry` and decorate `_call_llm_structured`.

```python
from app.core.shared.retry import with_retry

@with_retry()
async def _call_llm_structured(
    metric: Metric,
    system_prompt: str,
    user_prompt: str,
    response_schema: type[BaseModel],
) -> Any:
```

- [ ] **Step 2: Run test suite to verify no regressions**

Run: `uv run pytest tests/core/eval_engine/test_multi_step_evaluators.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/eval_engine/services/multi_step_evaluators.py
git commit -m "feat: decorate _call_llm_structured with with_retry"
```

---

### Task 3: Apply Retry to Document OCR Calls

**Files:**
- Modify: `backend/app/api/v1/endpoints/documents.py`

- [ ] **Step 1: Import with_retry and update OCR to be async with retries**

Modify `backend/app/api/v1/endpoints/documents.py` to:
1. Import `with_retry` from `app.core.shared.retry`.
2. Update the sync `client.models.generate_content` call to use the async client (`client.aio.models.generate_content`) wrapped with `@with_retry()`.

```python
        # Use Gemini OCR to extract text from PDF and images
        if not text_content.strip():
            try:
                from app.core.shared.retry import with_retry
                client = genai.Client()

                @with_retry()
                async def _call_gemini_ocr() -> types.GenerateContentResponse:
                    return await client.aio.models.generate_content(
                        model='gemini-3.1-flash-lite',
                        contents=[
                            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                            'Extract all text from this document/image. Preserve formatting where appropriate but output ONLY the raw extracted text. Do not add conversational filler, introductions, or markdown wraps. Output ONLY the extracted text contents.',
                        ],
                    )

                response = await _call_gemini_ocr()
                text_content = response.text or ''
```

- [ ] **Step 2: Run test suite to verify no regressions**

Run: `uv run pytest tests/core/eval_engine/test_runtime_state_extractor.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/endpoints/documents.py
git commit -m "feat: convert OCR document upload call to use async with_retry"
```
