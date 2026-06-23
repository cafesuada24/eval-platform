# Exponential Retry in `ai-chat` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a unified synchronous exponential retry backoff utility to handle transient exceptions (429 rate limit, 5xx server errors, timeouts, connections) on all LLM and embedding calls within the `ai-chat` module.

**Architecture:** We will create a new shared file `utils.py` containing retry helpers, and refactor existing modules (`embedder.py`, `rag_engine.py`, `parser.py`, and `benchmark.py`) to utilize them. We'll update the unit tests to mock specific retryable Exceptions (`APIError`/`ServerError`) and ensure that non-retryable exceptions fail immediately.

**Tech Stack:** Python 3.12, pytest, google-genai SDK

---

### Task 1: Create `utils.py` and `test_utils.py`

**Files:**
- Create: `ai-chat/utils.py`
- Create: `ai-chat/test_utils.py`

- [ ] **Step 1: Write the failing tests**

  Create `ai-chat/test_utils.py` with the following content:
  ```python
  from unittest.mock import MagicMock, patch
  import pytest
  from google.genai import errors as genai_errors
  from utils import is_retryable_exception, retry_api_call, with_retry

  def test_is_retryable_exception():
      # 1. Standard Python Exceptions
      assert is_retryable_exception(ConnectionError("connection failed")) is True
      assert is_retryable_exception(TimeoutError("timeout failed")) is True
      assert is_retryable_exception(ValueError("value error")) is False

      # 2. ServerError (5xx)
      assert is_retryable_exception(genai_errors.ServerError(code=503, response_json={})) is True

      # 3. APIError specific status codes
      assert is_retryable_exception(genai_errors.APIError(code=429, response_json={})) is True
      assert is_retryable_exception(genai_errors.APIError(code=500, response_json={})) is True
      assert is_retryable_exception(genai_errors.APIError(code=502, response_json={})) is True
      assert is_retryable_exception(genai_errors.APIError(code=503, response_json={})) is True
      assert is_retryable_exception(genai_errors.APIError(code=504, response_json={})) is True

      # Non-retryable client errors
      assert is_retryable_exception(genai_errors.APIError(code=400, response_json={})) is False
      assert is_retryable_exception(genai_errors.APIError(code=404, response_json={})) is False

  @patch("utils.time.sleep")
  def test_retry_api_call_success(mock_sleep):
      mock_func = MagicMock()
      mock_func.side_effect = [
          genai_errors.APIError(code=429, response_json={}),
          genai_errors.ServerError(code=503, response_json={}),
          "success"
      ]
      res = retry_api_call(mock_func, max_retries=2, initial_delay=1.0, use_jitter=False)
      assert res == "success"
      assert mock_func.call_count == 3
      assert mock_sleep.call_count == 2
      mock_sleep.assert_any_call(1.0)
      mock_sleep.assert_any_call(2.0)

  @patch("utils.time.sleep")
  def test_retry_api_call_non_retryable_raises(mock_sleep):
      mock_func = MagicMock()
      mock_func.side_effect = ValueError("permanent error")
      with pytest.raises(ValueError, match="permanent error"):
          retry_api_call(mock_func, max_retries=3)
      assert mock_func.call_count == 1
      assert mock_sleep.call_count == 0

  @patch("utils.time.sleep")
  def test_retry_api_call_exhausted(mock_sleep):
      mock_func = MagicMock()
      mock_func.side_effect = genai_errors.APIError(code=429, response_json={})
      with pytest.raises(genai_errors.APIError):
          retry_api_call(mock_func, max_retries=3, initial_delay=1.0, use_jitter=False)
      # 1 initial + 3 retries = 4 attempts total
      assert mock_func.call_count == 4
      assert mock_sleep.call_count == 3
      sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
      assert sleep_calls == [1.0, 2.0, 4.0]

  @patch("utils.time.sleep")
  def test_with_retry_decorator(mock_sleep):
      mock_func = MagicMock()
      mock_func.side_effect = [
          genai_errors.APIError(code=429, response_json={}),
          "decorator success"
      ]

      @with_retry(max_retries=2, initial_delay=1.0, use_jitter=False)
      def decorated_func(arg1, kwarg1=None):
          return mock_func(arg1, kwarg1=kwarg1)

      res = decorated_func("test", kwarg1="val")
      assert res == "decorator success"
      assert mock_func.call_count == 2
      mock_func.assert_called_with("test", kwarg1="val")
      assert mock_sleep.call_count == 1
      mock_sleep.assert_called_with(1.0)
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `uv run pytest test_utils.py`  
  Expected: FAIL with `ModuleNotFoundError: No module named 'utils'`

- [ ] **Step 3: Write minimal implementation**

  Create `ai-chat/utils.py` with the following content:
  ```python
  """Retry utilities for Gemini API and other network operations."""

  import functools
  import logging
  import random
  import time
  from collections.abc import Callable
  from typing import ParamSpec, TypeVar
  from google.genai import errors as genai_errors

  logger = logging.getLogger(__name__)

  T = TypeVar('T')
  P = ParamSpec('P')

  def is_retryable_exception(exc: BaseException) -> bool:
      """Checks if the exception is transient and can be retried.

      Retryable exceptions include:
      - ConnectionError and TimeoutError (standard library)
      - ServerError (from google-genai, which covers 5xx)
      - APIError (from google-genai) with status code 429 or 5xx
      """
      if isinstance(exc, (ConnectionError, TimeoutError)):
          return True

      if isinstance(exc, genai_errors.ServerError):
          return True

      if isinstance(exc, genai_errors.APIError):
          try:
              code = int(exc.code) if exc.code is not None else None
          except (ValueError, TypeError):
              code = None
          if code in (429, 500, 502, 503, 504):
              return True

      return False

  def retry_api_call(
      func: Callable[[], T],
      max_retries: int = 3,
      initial_delay: float = 1.0,
      max_delay: float = 30.0,
      use_jitter: bool = True,
  ) -> T:
      """Executes a function with exponential backoff and optional jitter on transient errors."""
      delay = initial_delay
      for attempt in range(1, max_retries + 2):
          try:
              return func()
          except BaseException as e:
              if not is_retryable_exception(e) or attempt == max_retries + 1:
                  if attempt == max_retries + 1:
                      logger.error(
                          "API call failed after %d attempts: %s",
                          max_retries + 1,
                          e,
                      )
                  raise

              backoff_limit = min(max_delay, delay)
              sleep_time = (
                  random.uniform(0, backoff_limit) if use_jitter else backoff_limit
              )

              logger.warning(
                  "API call failed (attempt %d/%d) with %s: %s. Retrying in %.2fs...",
                  attempt,
                  max_retries + 1,
                  type(e).__name__,
                  e,
                  sleep_time,
              )
              time.sleep(sleep_time)
              delay *= 2.0
      raise RuntimeError("Unreachable")

  def with_retry(
      max_retries: int = 3,
      initial_delay: float = 1.0,
      max_delay: float = 30.0,
      use_jitter: bool = True,
  ) -> Callable[[Callable[P, T]], Callable[P, T]]:
      """Decorator to apply retry logic to a function on transient errors."""
      def decorator(func: Callable[P, T]) -> Callable[P, T]:
          @functools.wraps(func)
          def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
              return retry_api_call(
                  lambda: func(*args, **kwargs),
                  max_retries=max_retries,
                  initial_delay=initial_delay,
                  max_delay=max_delay,
                  use_jitter=use_jitter,
              )
          return wrapper
      return decorator
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `uv run pytest test_utils.py`  
  Expected: PASS

- [ ] **Step 5: Commit**

  Run:
  ```bash
  git add utils.py test_utils.py
  git commit -m "feat: implement unified exponential backoff retry utility and unit tests"
  ```

---

### Task 2: Integrate Retry in `embedder.py` and Update Tests

**Files:**
- Modify: `ai-chat/embedder.py`
- Modify: `ai-chat/test_embedder.py`

- [ ] **Step 1: Write the failing tests in `test_embedder.py`**

  In `ai-chat/test_embedder.py`, update `test_generate_embeddings_retry_success` and `test_generate_embeddings_retry_failure` to use `google.genai.errors.APIError` or `google.genai.errors.ServerError`. Add a new test verifying generic exceptions do NOT retry.

  Replace lines 81 to 140 of `ai-chat/test_embedder.py` with:
  ```python
  from google.genai import errors as genai_errors

  @patch('embedder.time.sleep')
  @patch('embedder.genai.Client')
  def test_generate_embeddings_retry_success(
      mock_client_class: MagicMock,
      mock_sleep: MagicMock,
  ) -> None:
      """Test retry behavior under rate limits/transient errors with eventual success."""
      mock_client = MagicMock()
      mock_client_class.return_value = mock_client

      mock_embedding = MagicMock()
      mock_embedding.values = SINGLE_VALS
      mock_response = MagicMock()
      mock_response.embeddings = [mock_embedding]

      # Fails twice (retryable status codes), then succeeds on 3rd attempt
      mock_client.models.embed_content.side_effect = [
          genai_errors.APIError(code=429, response_json={}),
          genai_errors.ServerError(code=503, response_json={}),
          mock_response,
      ]

      res = generate_embeddings(['hello'])
      assert res == [SINGLE_VALS]
      assert mock_client.models.embed_content.call_count == EXPECTED_CALLS_3
      assert mock_sleep.call_count == EXPECTED_SLEEPS_2

  @patch('embedder.time.sleep')
  @patch('embedder.genai.Client')
  def test_generate_embeddings_retry_failure(
      mock_client_class: MagicMock,
      mock_sleep: MagicMock,
  ) -> None:
      """Test that after max retries fail, the exception is propagated."""
      mock_client = MagicMock()
      mock_client_class.return_value = mock_client

      # Fails all 4 attempts (initial + 3 retries) with 429 errors
      mock_client.models.embed_content.side_effect = [
          genai_errors.APIError(code=429, response_json={}) for _ in range(4)
      ]

      with pytest.raises(genai_errors.APIError):
          generate_embeddings(['hello'])

      assert mock_client.models.embed_content.call_count == EXPECTED_CALLS_4
      assert mock_sleep.call_count == EXPECTED_SLEEPS_3

  @patch('embedder.time.sleep')
  @patch('embedder.genai.Client')
  def test_generate_embeddings_non_retryable_raises_immediately(
      mock_client_class: MagicMock,
      mock_sleep: MagicMock,
  ) -> None:
      """Test that a non-retryable exception is not retried and propagates immediately."""
      mock_client = MagicMock()
      mock_client_class.return_value = mock_client
      mock_client.models.embed_content.side_effect = ValueError("non-retryable error")

      with pytest.raises(ValueError, match="non-retryable error"):
          generate_embeddings(['hello'])

      assert mock_client.models.embed_content.call_count == 1
      assert mock_sleep.call_count == 0
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `uv run pytest test_embedder.py`  
  Expected: FAIL (because the embedder still retries on ValueError, or doesn't support the mock APIErrors correctly)

- [ ] **Step 3: Modify `embedder.py`**

  Modify `_cached_generate_embeddings` in `ai-chat/embedder.py` to use `retry_api_call` (use `use_jitter=False` for test consistency in delay checks or allow default `use_jitter=True` in production, wait: the tests in `test_embedder.py` assert `mock_sleep.call_count` but do not mock the delay values themselves, except by patching `sleep`. Since we patch `sleep`, the jitter doesn't affect assertion counts).
  Let's use `use_jitter=False` inside unit tests if we want to test exact backoff times or patch random. But since the sleep is patched, `mock_sleep.call_count` is identical.
  Replace lines 10 to 56 of `ai-chat/embedder.py` with:
  ```python
  from utils import retry_api_call

  @lru_cache(maxsize=1024)
  def _cached_generate_embeddings(texts_tuple: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
      """Internal helper to batch and embed contents, cached via lru_cache."""
      if not texts_tuple:
          return ()

      client = genai.Client()
      max_retries = 3
      batch_size = 100
      all_embeddings = []

      for i in range(0, len(texts_tuple), batch_size):
          batch_texts = texts_tuple[i : i + batch_size]
          
          def run_batch():
              contents = [
                  types.Content(parts=[types.Part.from_text(text=t)])
                  for t in batch_texts
              ]
              response = client.models.embed_content(
                  model='gemini-embedding-2',
                  contents=contents,
              )
              embeddings = response.embeddings
              if not embeddings:
                  raise ValueError("Failed to retrieve embeddings from API response.")
              
              batch_vals = [
                  tuple(embedding.values)
                  for embedding in embeddings
                  if embedding.values is not None
              ]
              
              if len(batch_vals) != len(batch_texts):
                  raise ValueError(f"Mismatch in returned embeddings count. Expected {len(batch_texts)}, got {len(batch_vals)}")
              return batch_vals

          # We set use_jitter=False in embedder to ensure tests asserting standard delays remain deterministic
          batch_vals = retry_api_call(
              run_batch,
              max_retries=max_retries,
              initial_delay=1.0,
              use_jitter=False,
          )
          all_embeddings.extend(batch_vals)

      return tuple(all_embeddings)
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `uv run pytest test_embedder.py`  
  Expected: PASS

- [ ] **Step 5: Commit**

  Run:
  ```bash
  git add embedder.py test_embedder.py
  git commit -m "refactor: refactor embedder to use utils.retry_api_call and update tests"
  ```

---

### Task 3: Integrate Retry in `rag_engine.py` and Update Tests

**Files:**
- Modify: `ai-chat/rag_engine.py`
- Modify: `ai-chat/test_rag_engine.py`

- [ ] **Step 1: Write the failing tests in `test_rag_engine.py`**

  In `ai-chat/test_rag_engine.py`, update `test_generate_answer_forced_retries` and `test_generate_answer_forced_retries_exhausted` to raise `google.genai.errors.APIError` (code 429) instead of `Exception`. Also add a test verifying ValueError is not retried.

  Replace lines 150 to 206 of `ai-chat/test_rag_engine.py` with:
  ```python
  from google.genai import errors as genai_errors

  @patch("rag_engine.time.sleep")
  @patch("rag_engine.retrieve_context")
  @patch("rag_engine.genai.Client")
  def test_generate_answer_forced_retries(
      mock_client_class: MagicMock,
      mock_retrieve: MagicMock,
      mock_sleep: MagicMock,
  ) -> None:
      """force_retrieve=True: retries with exponential backoff on transient errors."""
      mock_state = MagicMock(spec=RuntimeState)
      mock_gen_tracker = MagicMock()
      mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

      mock_retrieve.return_value = ("ctx", [])

      mock_client = MagicMock()
      mock_client_class.return_value = mock_client
      mock_response = MagicMock()
      mock_response.text = "Answer on retry"
      mock_response.usage_metadata = None

      mock_client.models.generate_content.side_effect = [
          genai_errors.APIError(code=429, response_json={}),
          genai_errors.ServerError(code=503, response_json={}),
          mock_response,
      ]

      answer = generate_answer(mock_state, "query", force_retrieve=True)

      assert answer == "Answer on retry"
      assert mock_client.models.generate_content.call_count == 3
      assert mock_sleep.call_count == 2
      mock_sleep.assert_any_call(1.0)
      mock_sleep.assert_any_call(2.0)

  @patch("rag_engine.time.sleep")
  @patch("rag_engine.retrieve_context")
  @patch("rag_engine.genai.Client")
  def test_generate_answer_forced_retries_exhausted(
      mock_client_class: MagicMock,
      mock_retrieve: MagicMock,
      mock_sleep: MagicMock,
  ) -> None:
      """force_retrieve=True: propagates exception after max retries."""
      mock_state = MagicMock(spec=RuntimeState)
      mock_gen_tracker = MagicMock()
      mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

      mock_retrieve.return_value = ("ctx", [])

      mock_client = MagicMock()
      mock_client_class.return_value = mock_client
      mock_client.models.generate_content.side_effect = [
          genai_errors.APIError(code=429, response_json={}) for _ in range(4)
      ]

      with pytest.raises(genai_errors.APIError):
          generate_answer(mock_state, "query", force_retrieve=True)

      assert mock_client.models.generate_content.call_count == 4
      sleep_args = [c[0][0] for c in mock_sleep.call_args_list]
      assert sleep_args == [1.0, 2.0, 4.0]

  @patch("rag_engine.time.sleep")
  @patch("rag_engine.retrieve_context")
  @patch("rag_engine.genai.Client")
  def test_generate_answer_non_retryable_fails_immediately(
      mock_client_class: MagicMock,
      mock_retrieve: MagicMock,
      mock_sleep: MagicMock,
  ) -> None:
      """force_retrieve=True: fails immediately on non-retryable exception."""
      mock_state = MagicMock(spec=RuntimeState)
      mock_gen_tracker = MagicMock()
      mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker
      mock_retrieve.return_value = ("ctx", [])

      mock_client = MagicMock()
      mock_client_class.return_value = mock_client
      mock_client.models.generate_content.side_effect = ValueError("invalid prompt")

      with pytest.raises(ValueError, match="invalid prompt"):
          generate_answer(mock_state, "query", force_retrieve=True)

      assert mock_client.models.generate_content.call_count == 1
      assert mock_sleep.call_count == 0
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `uv run pytest test_rag_engine.py`  
  Expected: FAIL

- [ ] **Step 3: Modify `rag_engine.py`**

  Update `_call_generate_content_with_retry` in `ai-chat/rag_engine.py` to use `retry_api_call` (use `use_jitter=False` to preserve test assertions on sleep times).
  Replace lines 116 to 137 of `ai-chat/rag_engine.py` with:
  ```python
  from utils import retry_api_call

  def _call_generate_content_with_retry(
      client: genai.Client,
      **kwargs: Any,
  ) -> types.GenerateContentResponse:
      """Calls client.models.generate_content with exponential backoff retry."""
      return retry_api_call(
          lambda: client.models.generate_content(**kwargs),
          max_retries=MAX_RETRIES,
          initial_delay=INITIAL_DELAY,
          use_jitter=False,
      )
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `uv run pytest test_rag_engine.py`  
  Expected: PASS

- [ ] **Step 5: Commit**

  Run:
  ```bash
  git add rag_engine.py test_rag_engine.py
  git commit -m "refactor: refactor rag_engine content generation calls to use utils.retry_api_call"
  ```

---

### Task 4: Integrate Retry in `parser.py` and Update Tests

**Files:**
- Modify: `ai-chat/parser.py`
- Modify: `ai-chat/test_parser.py`

- [ ] **Step 1: Write the failing tests in `test_parser.py`**

  In `ai-chat/test_parser.py`, update `test_extract_and_caption_bytes_failure` to mock raise `APIError` and add another test verifying that `ValueError` raises immediately.

  Replace lines 263 to 278 of `ai-chat/test_parser.py` with:
  ```python
  from google.genai import errors as genai_errors

  @patch("parser.time.sleep")
  @patch("parser.genai.Client")
  def test_extract_and_caption_bytes_failure(mock_genai_client_class, mock_sleep):
      mock_client = MagicMock()
      mock_genai_client_class.return_value = mock_client
      mock_client.models.generate_content.side_effect = genai_errors.APIError(code=429, response_json={})

      with pytest.raises(genai_errors.APIError):
          extract_and_caption_bytes(b"dummy bytes", "image/png")

      assert mock_client.models.generate_content.call_count == 4
      assert mock_sleep.call_count == 3
      sleep_args = [c[0][0] for c in mock_sleep.call_args_list]
      assert sleep_args == [1.0, 2.0, 4.0]

  @patch("parser.time.sleep")
  @patch("parser.genai.Client")
  def test_extract_and_caption_bytes_non_retryable_failure(mock_genai_client_class, mock_sleep):
      mock_client = MagicMock()
      mock_genai_client_class.return_value = mock_client
      mock_client.models.generate_content.side_effect = ValueError("API failure")

      with pytest.raises(ValueError, match="API failure"):
          extract_and_caption_bytes(b"dummy bytes", "image/png")

      assert mock_client.models.generate_content.call_count == 1
      assert mock_sleep.call_count == 0
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `uv run pytest test_parser.py`  
  Expected: FAIL

- [ ] **Step 3: Modify `parser.py`**

  Modify `extract_and_caption_bytes` in `ai-chat/parser.py` to use `retry_api_call` (use `use_jitter=False` for test consistency).
  Replace lines 50 to 83 of `ai-chat/parser.py` with:
  ```python
  from utils import retry_api_call

  def extract_and_caption_bytes(image_bytes: bytes, mime_type: str) -> ExtractionResult:
      """Uses Gemini API to perform both OCR (raw text extraction) and visual captioning in one structured response."""
      client = genai.Client()

      prompt = (
          "Analyze this document page/image. Perform OCR to extract all readable text exactly, "
          "and write a detailed descriptive caption for any charts, diagrams, drawings, or figures."
      )

      def run_ocr():
          response = client.models.generate_content(
              model="gemini-3.1-flash-lite",
              contents=[
                  genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                  prompt,
              ],  # type: ignore[arg-type]
              config=genai.types.GenerateContentConfig(
                  response_mime_type="application/json",
                  response_schema=ExtractionResult,
              ),
          )
          if response and response.text:
              return ExtractionResult.model_validate_json(response.text.strip())
          raise ValueError("Empty response received from GenAI model.")

      try:
          return retry_api_call(
              run_ocr,
              max_retries=3,
              initial_delay=1.0,
              use_jitter=False,
          )
      except Exception as e:
          print(f"Failed to extract and caption bytes after 3 retries: {e}")
          raise e
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `uv run pytest test_parser.py`  
  Expected: PASS

- [ ] **Step 5: Commit**

  Run:
  ```bash
  git add parser.py test_parser.py
  git commit -m "refactor: refactor parser ocr caption helper to use utils.retry_api_call"
  ```

---

### Task 5: Integrate in `benchmark.py` and Verify Entire Project

**Files:**
- Modify: `ai-chat/benchmark.py`

- [ ] **Step 1: Modify `benchmark.py`**

  Remove local `retry_api_call` function definition and instead import `retry_api_call` from `utils`.
  Remove lines 68 to 89 from `ai-chat/benchmark.py`.
  Add import statement:
  ```python
  from utils import retry_api_call
  ```
  to the top import block in `ai-chat/benchmark.py`.

- [ ] **Step 2: Run all tests to verify success**

  Run: `uv run pytest`  
  Expected: PASS (41+ tests passing)

- [ ] **Step 3: Commit**

  Run:
  ```bash
  git add benchmark.py
  git commit -m "refactor: replace benchmark local retry_api_call with unified utility"
  ```
