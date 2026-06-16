# Agentic RAG Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardwired `retrieve_context() → generate_answer()` pipeline with a Gemini Function Calling loop so the LLM decides whether to retrieve, while preserving forced-retrieval behaviour for the evaluation pipeline.

**Architecture:** `generate_answer()` in `rag_engine.py` is rewritten to own the full tool-call loop. It accepts a `force_retrieve: bool = False` flag. When `False`, it sends the query to Gemini with a `retrieve_documents` tool declaration; if the model calls the tool, it invokes `retrieve_context()` and sends a second request with the results. When `True`, it calls `retrieve_context()` unconditionally (eval path). `main.py` is updated to remove its own `retrieve_context()` calls.

**Tech Stack:** Python 3.12, `google-genai` SDK (`google.genai.types.FunctionDeclaration`, `Tool`, `Part.from_function_response`), `evalplatform_sdk`, `pytest` + `unittest.mock`.

**Worktree:** `.worktrees/feat-agentic-rag` on branch `feat/agentic-rag-tool`

**Baseline:** 37 tests passing before any changes.

**Spec:** [`docs/superpowers/specs/2026-06-16-agentic-rag-tool-design.md`](../specs/2026-06-16-agentic-rag-tool-design.md)

---

## File Map

| File | Action | What changes |
|---|---|---|
| `ai-chat/rag_engine.py` | **Modify** | Rewrite `generate_answer()`: new signature, tool declaration, two-path logic, tool-call loop |
| `ai-chat/main.py` | **Modify** | Chat tab: remove `retrieve_context()` call, simplify to `generate_answer(state, prompt)`. Eval tab: add `force_retrieve=True`. Remove `retrieve_context` import. |
| `ai-chat/test_rag_engine.py` | **Modify** | Update/replace the four `generate_answer` tests to match new signature and two-path behaviour |

---

## Task 1: Rewrite `generate_answer()` — forced path

Update the function signature and implement `force_retrieve=True` path first. This keeps all existing tests passing (we'll update them in Task 2).

**Files:**
- Modify: `ai-chat/rag_engine.py` (full function replacement)

- [ ] **Step 1: Replace `generate_answer()` in `rag_engine.py`**

  Replace the entire function with the implementation below. The `image_paths` parameter is gone from the signature — image paths are now sourced internally from `retrieve_context()`.

  Note: `from google.genai import types` must be added to the imports block.

  ```python
  # Add to imports at top of file (after existing google import):
  from google.genai import types
  ```

  Replace the full `generate_answer` function body:

  ```python
  def generate_answer(state: RuntimeState, query: str, force_retrieve: bool = False) -> str:
      """Generates an answer using Gemini, with optional agentic retrieval.

      When force_retrieve=True (eval path): calls retrieve_context() unconditionally,
      then generates with context injected into the prompt.

      When force_retrieve=False (chat path): lets Gemini decide via Function Calling
      whether to call retrieve_documents. If it does, retrieve_context() is called
      and results injected; otherwise the model answers directly.

      Tracks LLM execution using state generation context manager.
      Handles transient errors with retries on all generate_content() calls.
      """
      model_name = "gemini-3.1-flash-lite"
      client = genai.Client()

      with state.track_generation() as gen_tracker:
          gen_tracker.model_info(provider="google", model_name=model_name)
          gen_tracker.user_input(query)

          if force_retrieve:
              answer = _generate_with_forced_retrieval(
                  state, client, gen_tracker, model_name, query
              )
          else:
              answer = _generate_agentic(
                  state, client, gen_tracker, model_name, query
              )

          gen_tracker.output_text(answer)
          return answer


  def _call_generate_content_with_retry(client: genai.Client, **kwargs: object) -> object:
      """Calls client.models.generate_content with exponential backoff retry."""
      max_retries = 3
      delay = 1.0
      for attempt in range(max_retries + 1):
          try:
              return client.models.generate_content(**kwargs)  # type: ignore[arg-type]
          except Exception as e:
              if attempt == max_retries:
                  raise e
              time.sleep(delay)
              delay *= 2.0


  def _generate_with_forced_retrieval(
      state: RuntimeState,
      client: genai.Client,
      gen_tracker: object,
      model_name: str,
      query: str,
  ) -> str:
      """Forced-retrieval path: always calls retrieve_context() before generation."""
      context, image_paths = retrieve_context(state, query)

      loaded_images = _load_images(image_paths)
      prompt_text = _build_rag_prompt(query, context)
      contents = [*loaded_images, prompt_text]

      response = _call_generate_content_with_retry(
          client, model=model_name, contents=contents
      )

      _record_token_usage(gen_tracker, response)
      return response.text or ""


  def _generate_agentic(
      state: RuntimeState,
      client: genai.Client,
      gen_tracker: object,
      model_name: str,
      query: str,
  ) -> str:
      """Agentic path: Gemini decides whether to call retrieve_documents tool."""
      retrieve_tool = types.Tool(
          function_declarations=[
              types.FunctionDeclaration(
                  name="retrieve_documents",
                  description=(
                      "Search the document knowledge base for information relevant to "
                      "the user's question. Call this when the question requires factual "
                      "information from uploaded documents."
                  ),
                  parameters=types.Schema(
                      type=types.Type.OBJECT,
                      properties={
                          "query": types.Schema(
                              type=types.Type.STRING,
                              description="The search query to run against the document store.",
                          )
                      },
                      required=["query"],
                  ),
              )
          ]
      )

      system_instruction = (
          "You are a helpful AI assistant. "
          "If the user's question requires information from uploaded documents, "
          "call the retrieve_documents tool. "
          "If you can answer from your own knowledge, respond directly."
      )

      # First call: let the model decide
      response = _call_generate_content_with_retry(
          client,
          model=model_name,
          contents=query,
          tools=[retrieve_tool],
          config=types.GenerateContentConfig(system_instruction=system_instruction),
      )

      # Check if the model called the tool
      function_call = _extract_function_call(response)

      if function_call is None:
          # Model answered directly — no retrieval needed
          _record_token_usage(gen_tracker, response)
          return response.text or ""

      # Model called retrieve_documents — execute it
      tool_query = function_call.get("query", query)
      if not isinstance(tool_query, str):
          logger.warning("retrieve_documents called with non-string query; using original query")
          tool_query = query

      context, image_paths = retrieve_context(state, tool_query)

      # Second call: send tool result back to model
      loaded_images = _load_images(image_paths)
      tool_result_part = types.Part.from_function_response(
          name="retrieve_documents",
          response={"context": context},
      )

      follow_up_contents = [
          types.Content(role="user", parts=[types.Part.from_text(text=query)]),
          response.candidates[0].content,  # model's function_call turn
          types.Content(role="user", parts=[tool_result_part]),
      ]

      final_response = _call_generate_content_with_retry(
          client,
          model=model_name,
          contents=follow_up_contents,
          config=types.GenerateContentConfig(system_instruction=system_instruction),
      )

      _record_token_usage(gen_tracker, final_response)
      return final_response.text or ""


  def _extract_function_call(response: object) -> dict | None:
      """Extracts function call args from response, or returns None if not present."""
      try:
          for part in response.candidates[0].content.parts:
              if hasattr(part, "function_call") and part.function_call:
                  return dict(part.function_call.args)
      except (AttributeError, IndexError, TypeError):
          pass
      return None


  def _load_images(image_paths: list[str]) -> list[Image.Image]:
      """Loads PIL images from paths, skipping ones that fail."""
      images = []
      for path in image_paths:
          try:
              images.append(Image.open(path))
          except Exception as e:
              logger.error("Failed to open image at %s: %s", path, e)
      return images


  def _build_rag_prompt(query: str, context: str) -> str:
      """Builds the RAG prompt string for forced-retrieval generation."""
      return (
          "You are a helpful AI assistant. Answer the user's question based ONLY on the provided context.\n"
          "If you cannot answer the question based on the context, say "
          '"I don\'t have enough information to answer that."\n\n'
          f"Context:\n{context}\n\nQuestion:\n{query}\n"
      )


  def _record_token_usage(gen_tracker: object, response: object) -> None:
      """Records token usage telemetry if usage metadata is present."""
      if response.usage_metadata:
          gen_tracker.token_usage(
              input_tokens=response.usage_metadata.prompt_token_count,
              output_tokens=response.usage_metadata.candidates_token_count,
          )
  ```

- [ ] **Step 2: Verify the module imports cleanly**

  ```bash
  cd ai-chat && uv run python -c "from rag_engine import generate_answer, retrieve_context; print('ok')"
  ```

  Expected: `ok` (no ImportError or SyntaxError)

---

## Task 2: Update tests for `generate_answer()`

The four existing `generate_answer` tests use the old signature `(state, query, context, image_paths)`. We replace them with tests covering the new two-path API.

**Files:**
- Modify: `ai-chat/test_rag_engine.py`

- [ ] **Step 1: Write failing tests for the new `generate_answer()` API**

  Replace the four existing `generate_answer` tests (functions: `test_generate_answer_success`, `test_generate_answer_retries_and_succeeds`, `test_generate_answer_retries_failure`) plus add new agentic-path tests.

  Delete from `test_rag_engine.py`:
  - `test_generate_answer_success`
  - `test_generate_answer_retries_and_succeeds`
  - `test_generate_answer_retries_failure`

  Add the following tests in their place:

  ```python
  # ── Forced-retrieval path ────────────────────────────────────────────────────

  @patch("rag_engine.retrieve_context")
  @patch("rag_engine.genai.Client")
  def test_generate_answer_forced_retrieval(
      mock_client_class: MagicMock, mock_retrieve: MagicMock
  ) -> None:
      """force_retrieve=True: always calls retrieve_context and returns model answer."""
      mock_state = MagicMock(spec=RuntimeState)
      mock_gen_tracker = MagicMock()
      mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

      mock_retrieve.return_value = ("some context text", [])

      mock_client = MagicMock()
      mock_client_class.return_value = mock_client
      mock_response = MagicMock()
      mock_response.text = "Forced answer"
      mock_response.usage_metadata = None
      mock_client.models.generate_content.return_value = mock_response

      answer = generate_answer(mock_state, "What is X?", force_retrieve=True)

      assert answer == "Forced answer"
      mock_retrieve.assert_called_once_with(mock_state, "What is X?")
      mock_client.models.generate_content.assert_called_once()
      # Verify context injected into prompt
      call_contents = mock_client.models.generate_content.call_args[1]["contents"]
      prompt = call_contents[-1]
      assert "some context text" in prompt
      assert "What is X?" in prompt


  @patch("rag_engine.retrieve_context")
  @patch("rag_engine.genai.Client")
  def test_generate_answer_forced_retrieval_logs_tokens(
      mock_client_class: MagicMock, mock_retrieve: MagicMock
  ) -> None:
      """force_retrieve=True: records token usage when usage_metadata is present."""
      mock_state = MagicMock(spec=RuntimeState)
      mock_gen_tracker = MagicMock()
      mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

      mock_retrieve.return_value = ("ctx", [])

      mock_client = MagicMock()
      mock_client_class.return_value = mock_client
      mock_response = MagicMock()
      mock_response.text = "Answer"
      mock_response.usage_metadata.prompt_token_count = 50
      mock_response.usage_metadata.candidates_token_count = 20
      mock_client.models.generate_content.return_value = mock_response

      generate_answer(mock_state, "query", force_retrieve=True)

      mock_gen_tracker.token_usage.assert_called_once_with(input_tokens=50, output_tokens=20)


  @patch("rag_engine.time.sleep")
  @patch("rag_engine.retrieve_context")
  @patch("rag_engine.genai.Client")
  def test_generate_answer_forced_retries_and_succeeds(
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
          Exception("API Error 1"),
          Exception("API Error 2"),
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
          Exception("E1"), Exception("E2"), Exception("E3"), Exception("E4"),
      ]

      with pytest.raises(Exception, match="E4"):
          generate_answer(mock_state, "query", force_retrieve=True)

      assert mock_client.models.generate_content.call_count == 4
      sleep_args = [c[0][0] for c in mock_sleep.call_args_list]
      assert sleep_args == [1.0, 2.0, 4.0]


  # ── Agentic path ─────────────────────────────────────────────────────────────

  def _make_direct_response(text: str) -> MagicMock:
      """Helper: mock response where model answers directly (no function call)."""
      response = MagicMock()
      response.text = text
      response.usage_metadata = None
      # No function_call on any part
      part = MagicMock()
      part.function_call = None
      response.candidates = [MagicMock()]
      response.candidates[0].content.parts = [part]
      return response


  def _make_tool_call_response(query_arg: str) -> MagicMock:
      """Helper: mock response where model calls retrieve_documents."""
      response = MagicMock()
      response.text = None
      response.usage_metadata = None
      fc = MagicMock()
      fc.args = {"query": query_arg}
      part = MagicMock()
      part.function_call = fc
      response.candidates = [MagicMock()]
      response.candidates[0].content.parts = [part]
      return response


  @patch("rag_engine.retrieve_context")
  @patch("rag_engine.genai.Client")
  def test_generate_answer_agentic_no_retrieval(
      mock_client_class: MagicMock, mock_retrieve: MagicMock
  ) -> None:
      """Agentic path: model answers directly without calling the tool."""
      mock_state = MagicMock(spec=RuntimeState)
      mock_gen_tracker = MagicMock()
      mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

      mock_client = MagicMock()
      mock_client_class.return_value = mock_client
      mock_client.models.generate_content.return_value = _make_direct_response("Hi there!")

      answer = generate_answer(mock_state, "Hi!")

      assert answer == "Hi there!"
      mock_retrieve.assert_not_called()
      mock_client.models.generate_content.assert_called_once()


  @patch("rag_engine.retrieve_context")
  @patch("rag_engine.genai.Client")
  def test_generate_answer_agentic_triggers_retrieval(
      mock_client_class: MagicMock, mock_retrieve: MagicMock
  ) -> None:
      """Agentic path: model calls retrieve_documents; second LLM call returns final answer."""
      mock_state = MagicMock(spec=RuntimeState)
      mock_gen_tracker = MagicMock()
      mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

      mock_retrieve.return_value = ("retrieved context", [])

      mock_client = MagicMock()
      mock_client_class.return_value = mock_client

      tool_call_resp = _make_tool_call_response("Paul Graham essays")
      final_resp = MagicMock()
      final_resp.text = "Final grounded answer"
      final_resp.usage_metadata = None

      mock_client.models.generate_content.side_effect = [tool_call_resp, final_resp]

      answer = generate_answer(mock_state, "What did Paul Graham write about?")

      assert answer == "Final grounded answer"
      mock_retrieve.assert_called_once_with(mock_state, "Paul Graham essays")
      assert mock_client.models.generate_content.call_count == 2


  @patch("rag_engine.retrieve_context")
  @patch("rag_engine.genai.Client")
  def test_generate_answer_agentic_bad_tool_args_falls_back(
      mock_client_class: MagicMock, mock_retrieve: MagicMock
  ) -> None:
      """Agentic path: malformed tool call (missing query) falls back to original query."""
      mock_state = MagicMock(spec=RuntimeState)
      mock_gen_tracker = MagicMock()
      mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

      mock_retrieve.return_value = ("ctx", [])

      mock_client = MagicMock()
      mock_client_class.return_value = mock_client

      # Tool call with no 'query' key
      bad_tool_resp = MagicMock()
      bad_tool_resp.text = None
      bad_tool_resp.usage_metadata = None
      fc = MagicMock()
      fc.args = {}  # missing 'query'
      part = MagicMock()
      part.function_call = fc
      bad_tool_resp.candidates = [MagicMock()]
      bad_tool_resp.candidates[0].content.parts = [part]

      final_resp = MagicMock()
      final_resp.text = "Fallback answer"
      final_resp.usage_metadata = None

      mock_client.models.generate_content.side_effect = [bad_tool_resp, final_resp]

      answer = generate_answer(mock_state, "original query")

      assert answer == "Fallback answer"
      # retrieve_context called with original query as fallback
      mock_retrieve.assert_called_once_with(mock_state, "original query")
  ```

- [ ] **Step 2: Run tests — expect failures**

  ```bash
  cd ai-chat && uv run pytest test_rag_engine.py -v 2>&1 | tail -25
  ```

  Expected: `retrieve_context` tests still pass (5 pass), new `generate_answer` tests fail because implementation isn't in place yet. Confirm tests are being collected and failing for the right reason (signature mismatch or import error).

  > **Note:** If Task 1 was completed before this step, most tests should already pass. This step exists to confirm the tests are wired correctly.

- [ ] **Step 3: Run full test suite — confirm no regressions**

  ```bash
  cd ai-chat && uv run pytest --tb=short -q 2>&1 | tail -10
  ```

  Expected: all tests pass (count will be higher than 37 due to new tests added).

- [ ] **Step 4: Commit**

  ```bash
  cd ai-chat && git add rag_engine.py test_rag_engine.py && git commit -m "feat: rewrite generate_answer() as Gemini Function Calling tool loop"
  ```

---

## Task 3: Update `main.py`

Remove `retrieve_context()` from `main.py`. The chat tab simplifies to one call; the eval tab adds `force_retrieve=True`.

**Files:**
- Modify: `ai-chat/main.py`

- [ ] **Step 1: Update the chat tab (lines ~96–98)**

  Find this block in `main.py`:
  ```python
  with trace() as state:
      context, image_paths = retrieve_context(state, prompt)
      answer = generate_answer(state, prompt, context, image_paths)
  ```

  Replace with:
  ```python
  with trace() as state:
      answer = generate_answer(state, prompt)
  ```

- [ ] **Step 2: Update the eval tab (lines ~208–211)**

  Find this block in `main.py`:
  ```python
  # Retrieve Context (Traces Retrieval Event internally)
  context, image_paths = retrieve_context(state, query)

  # Generate Response (Traces Generation Event internally)
  answer = generate_answer(state, query, context, image_paths)
  ```

  Replace with:
  ```python
  # Generate Response — forced retrieval ensures eval traces match historical behaviour
  answer = generate_answer(state, query, force_retrieve=True)
  ```

- [ ] **Step 3: Remove the `retrieve_context` import**

  Find in `main.py`:
  ```python
  from rag_engine import generate_answer, retrieve_context
  ```

  Replace with:
  ```python
  from rag_engine import generate_answer
  ```

- [ ] **Step 4: Verify no import or syntax errors**

  ```bash
  cd ai-chat && uv run python -c "import main" 2>&1 || echo "check output above"
  ```

  Expected: no output (module imports cleanly). Streamlit apps import at the top level — any error here is fatal.

- [ ] **Step 5: Run full test suite — final check**

  ```bash
  cd ai-chat && uv run pytest --tb=short -q 2>&1 | tail -10
  ```

  Expected: all tests pass with 0 failures.

- [ ] **Step 6: Commit**

  ```bash
  cd ai-chat && git add main.py && git commit -m "refactor: remove retrieve_context from main.py, use generate_answer directly"
  ```

---

## Task 4: Smoke test the Streamlit app

Manually verify the chat interface works end-to-end with the new agentic behaviour.

**Prerequisites:** `GEMINI_API_KEY` set in `.env`.

- [ ] **Step 1: Start the Streamlit app**

  ```bash
  cd ai-chat && uv run streamlit run main.py
  ```

  Expected: app opens at `http://localhost:8501` with no startup errors in terminal.

- [ ] **Step 2: Test direct-answer path (no documents loaded)**

  In the chat tab, send: `Hi, how are you?`

  Expected: the model answers conversationally without errors. No retrieval should occur (confirm by checking terminal — no ChromaDB query log).

- [ ] **Step 3: Test retrieval path**

  Upload a `.txt` file via the sidebar (any document). After ingestion, ask a question about its content.

  Expected: the model calls `retrieve_documents`, retrieves relevant chunks, and answers based on the document content.

- [ ] **Step 4: Stop the app**

  `Ctrl+C` in the terminal.

- [ ] **Step 5: Commit smoke test confirmation**

  ```bash
  cd ai-chat && git commit --allow-empty -m "chore: smoke test verified — agentic RAG tool working"
  ```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ `generate_answer()` signature change → Task 1
- ✅ Agentic path (Function Calling loop) → Task 1
- ✅ Forced path (`force_retrieve=True`) → Task 1
- ✅ `track_retrieval()` fires only when `retrieve_context()` called → Task 1 (retrieve_context unchanged)
- ✅ `track_generation()` always fires → Task 1 (wraps entire function)
- ✅ Malformed tool call fallback → Task 1 + test in Task 2
- ✅ Chat tab simplified → Task 3
- ✅ Eval tab uses `force_retrieve=True` → Task 3
- ✅ `retrieve_context` import removed from `main.py` → Task 3
- ✅ `test_rag_engine.py` updated → Task 2

**Placeholders:** None — all steps contain full code.

**Type consistency:** `generate_answer(state, query, force_retrieve=False)` used consistently across Tasks 1, 2, 3.
