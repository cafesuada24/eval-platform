# Agentic RAG Tool — Design Spec

**Date:** 2026-06-16
**Status:** Approved
**Scope:** `ai-chat/` module only

---

## Problem

`main.py` unconditionally calls `retrieve_context()` before every `generate_answer()` call. This means every user message — regardless of whether it needs document context — pays the full cost of embedding + ChromaDB vector search. Conversational queries like "Hi" or "Summarise what you just said" retrieve irrelevant chunks and add latency for no benefit.

## Goal

Turn `retrieve_context()` into a **Gemini Function Calling tool** that the LLM invokes only when it determines document context is needed. The evaluation pipeline must remain unaffected in behaviour.

---

## Architecture

### Entry Point

`generate_answer()` in `rag_engine.py` becomes the sole entry point for all query handling. It owns the tool-call loop and the decision of whether to retrieve.

Signature change:

```python
# Before
def generate_answer(state: RuntimeState, query: str, context: str, image_paths: list[str]) -> str

# After
def generate_answer(state: RuntimeState, query: str, force_retrieve: bool = False) -> str
```

`image_paths` is no longer a caller concern — if retrieval happens, image paths are resolved internally as part of the tool call.

---

### Two Execution Paths

#### Path 1 — Agentic (default, `force_retrieve=False`)

Used by the **chat tab** in `main.py`.

1. Define a `FunctionDeclaration` for `retrieve_documents`:
   - `name`: `"retrieve_documents"`
   - `description`: `"Search the document knowledge base for information relevant to the user's question. Call this when the question requires factual information from uploaded documents."`
   - `parameters`: `{ query: string }` (required)

2. Call `client.models.generate_content()` with `tools=[retrieve_documents_tool]` and no pre-fetched context in the prompt.

3. Inspect the response:
   - **No function call** → model answered from its own knowledge. Extract `response.text`, return it.
   - **Function call present** → extract the `query` argument, call `retrieve_context(state, query)` (which fires `track_retrieval()`), then call `generate_content()` a second time with the tool result injected. Extract `response.text` from the second response, return it.

4. The loop handles exactly one tool call. Multi-hop retrieval is out of scope for this iteration.

#### Path 2 — Forced (`force_retrieve=True`)

Used by the **evaluation tab** in `main.py`.

1. Call `retrieve_context(state, query)` directly — same as today. `track_retrieval()` fires.
2. Call `generate_content()` with the retrieved context injected into the prompt — same as today.
3. Return `response.text`.

This path is behaviourally identical to the current pipeline. Eval traces are unchanged.

---

### Tracing Behaviour

| Event | Agentic (no retrieval) | Agentic (retrieval triggered) | Forced |
|---|---|---|---|
| `track_generation()` | ✅ always | ✅ always | ✅ always |
| `track_retrieval()` | ❌ not fired | ✅ fired | ✅ fired |

`track_generation()` wraps the entire function in both paths. `track_retrieval()` fires only when `retrieve_context()` is actually called, ensuring traces are truthful.

---

### Changes to `main.py`

**Chat tab** (currently lines 96–98):

```python
# Before
with trace() as state:
    context, image_paths = retrieve_context(state, prompt)
    answer = generate_answer(state, prompt, context, image_paths)

# After
with trace() as state:
    answer = generate_answer(state, prompt)
```

**Eval tab** (currently lines 208–211):

```python
# Before
context, image_paths = retrieve_context(state, query)
answer = generate_answer(state, query, context, image_paths)

# After
answer = generate_answer(state, query, force_retrieve=True)
```

The `retrieve_context` import in `main.py` is removed after this change.

---

### What Does Not Change

| Component | Status |
|---|---|
| `retrieve_context()` in `rag_engine.py` | Unchanged internally |
| `vector_store.py` | Untouched |
| `embedder.py` | Untouched |
| `parser.py` | Untouched |
| Eval platform SDK tracing | Unchanged in behaviour |
| All test files | No changes needed |

---

## Error Handling

- If the model returns a malformed function call (missing `query` argument), log a warning and fall back to answering without context (treat as no-retrieval case).
- Retry logic for transient API errors remains as today — it wraps the `generate_content()` calls.
- If the second `generate_content()` call (after tool result injection) fails, the error propagates to `main.py` as today.

---

## Out of Scope

- Multi-hop retrieval (model calling the tool more than once per query)
- Adding more tools (e.g., web search)
- Streaming responses
- Changes to `benchmark.py` or eval test cases

---

## Files Modified

| File | Change |
|---|---|
| `rag_engine.py` | Rewrite `generate_answer()`: tool declaration, tool-call loop, `force_retrieve` flag |
| `main.py` | Simplify chat call; add `force_retrieve=True` to eval; remove `retrieve_context` import |

## Files Modified (Tests)

| File | Change |
|---|---|
| `test_rag_engine.py` | Update `generate_answer()` test calls to new signature (remove `context` and `image_paths` args; add `force_retrieve` cases) |

## Files Unchanged

`vector_store.py`, `embedder.py`, `parser.py`, `benchmark.py`, `test_parser.py`, `test_embedder.py`, `test_vector_store.py`.
