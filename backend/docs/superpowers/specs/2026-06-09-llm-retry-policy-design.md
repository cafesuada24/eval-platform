# Design Spec: Comprehensive LLM Retry Policy with Quota Handling

## Problem Statement
When running pipeline evaluations and document uploads under high concurrency or low quota limits, LLM requests fail with `litellm.BadRequestError` (often mapped from Gemini's quota limits) or transient quota errors. Currently, only some LLM calls have retry decorators, and those do not catch `litellm.BadRequestError` or have sufficient backoff attempts/delays for high concurrency.

## Objectives
- Apply a consistent exponential backoff retry policy to all LLM invocation paths.
- Catch `litellm.BadRequestError` during retry attempts.
- Enforce `max_attempts = 5` and `base_delay = 1.2` seconds across the system.

## Proposed Changes

### 1. `backend/app/core/shared/retry.py`
- Update `RETRYABLE_EXCEPTIONS` to include `litellm.BadRequestError` (so mapped bad requests/resource errors are retried).
- Change default arguments of `with_retry`:
  - `max_attempts = 5`
  - `base_delay = 1.2`

### 2. `backend/app/core/eval_engine/services/multi_step_evaluators.py`
- Import `with_retry` from `app.core.shared.retry`.
- Decorate `_call_llm_structured` with `@with_retry()`.

### 3. `backend/app/api/v1/endpoints/documents.py`
- Import `with_retry` from `app.core.shared.retry`.
- Convert the synchronous `client.models.generate_content` call inside `upload_file` to use `await client.aio.models.generate_content` wrapped in a `@with_retry()` decorated function.

## Verification & Testing
- Run all test suites:
  `uv run pytest tests/core/eval_engine/ -v`
