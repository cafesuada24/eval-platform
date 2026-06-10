# ChromaDB Interface Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the ChromaDB vector database storage and query interface module (`vector_store.py`) and its unit tests (`test_vector_store.py`).

**Architecture:** Wrap the `chromadb` client API using a persistent database client stored in `ai-chat/db`. The interface provides chunk addition with unique ID generation and metadata source tagging, and a query interface that adapts to the collection size.

**Tech Stack:** Python 3, ChromaDB, pytest, unittest.mock.

---

### Task 1: Create failing tests (RED)

**Files:**
- Create: `ai-chat/test_vector_store.py`

- [x] **Step 1: Write test file**
  Create `ai-chat/test_vector_store.py` containing tests verifying:
  - Mocking `chromadb.PersistentClient` and the collection.
  - `add_chunks_to_db` correctly generates unique IDs, maps the `source` to the `metadatas` using `meta.setdefault("source_file", source)`, validates matching list lengths, and calls `collection.add()`.
  - `add_chunks_to_db` handles empty chunks list by returning early.
  - `query_vector_store` calls `collection.query()` with the query vector and `n_results`.
  - `query_vector_store` handles collection count 0 gracefully (returns empty dictionary without querying).

- [x] **Step 2: Run tests to verify failure (Verify RED)**
  Run: `pytest test_vector_store.py` (working directory: `ai-chat/`)
  Expected: Failure because `vector_store` module and functions do not exist yet.

---

### Task 2: Implement vector store module (GREEN)

**Files:**
- Create: `ai-chat/vector_store.py`

- [x] **Step 3: Implement vector_store.py**
  Create `ai-chat/vector_store.py` containing:
  - Initialize `chromadb.PersistentClient` using persistent storage at the path `db/` (resolved dynamically to absolute path).
  - Get or create collection named `ai_chat_docs`.
  - Implement `add_chunks_to_db(chunks: list[str], embeddings: list[list[float]], metadatas: list[dict], source: str)`:
    - If `chunks` list is empty, return early.
    - If `metadatas` is not provided or empty, initialize it to empty dictionaries matching the number of chunks: `metadatas = [{} for _ in chunks]`.
    - Mutate each dictionary in `metadatas` using `meta.setdefault("source_file", source)`.
    - Assert length of chunks, embeddings, and metadatas match.
    - Generate unique string IDs (UUID4) for each chunk.
    - Call `collection.add(documents=chunks, embeddings=embeddings, metadatas=metadatas, ids=ids)`.
  - Implement `query_vector_store(query_vector: list[float], n_results: int = 3) -> dict`:
    - Check if collection count is 0. If so, return empty results dict.
    - Call `collection.query(query_embeddings=[query_vector], n_results=min(n_results, collection.count()))` and return the dictionary.

- [x] **Step 4: Run tests to verify they pass (Verify GREEN)**
  Run: `pytest test_vector_store.py` (working directory: `ai-chat/`)
  Expected: PASS.

---

### Task 3: Lint, Verify, and Commit

- [x] **Step 5: Run final checklist/linters**
  Verify code syntax, type hints, and formatting.
- [x] **Step 6: Git Add and Commit**
  Run: `git add vector_store.py test_vector_store.py` and commit changes.
