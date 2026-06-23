# AI Chat File Manager Sidebar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a file manager panel to the `ai-chat` Streamlit sidebar that lists all ChromaDB-indexed files, shows a tabbed detail panel (Overview / Chunks / Raw Content), and supports whole-file deletion with confirmation.

**Architecture:** ChromaDB is the single source of truth — `get_indexed_files()` queries `collection.get()` and groups by `source_file` metadata on every render. UI state (`selected_file`, `pending_delete`) lives in `st.session_state`. The detail panel is rendered as a right-hand `st.columns` split when a file is selected.

**Tech Stack:** Python 3.12, Streamlit, ChromaDB (`chromadb.PersistentClient`), pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `ai-chat/vector_store.py` | Modify | Add `get_indexed_files()` and `delete_file()` |
| `ai-chat/main.py` | Modify | Add file list sidebar section + detail panel column |
| `ai-chat/test_vector_store.py` | Modify | Add tests for the two new functions |

---

## Task 1: Add `get_indexed_files()` to `vector_store.py`

**Files:**
- Modify: `ai-chat/vector_store.py`
- Test: `ai-chat/test_vector_store.py`

- [ ] **Step 1: Write the failing tests**

Open `ai-chat/test_vector_store.py` and add at the end:

```python
from vector_store import get_indexed_files, delete_file


class TestGetIndexedFiles:
    """Tests for get_indexed_files()."""

    def test_returns_empty_dict_when_collection_empty(self, clean_collection):
        result = get_indexed_files()
        assert result == {}

    def test_groups_chunks_by_source_file(self, clean_collection):
        # Arrange — add 2 chunks for file_a and 1 for file_b
        clean_collection.add(
            documents=["chunk 1", "chunk 2", "chunk 3"],
            embeddings=[[0.1] * 768, [0.2] * 768, [0.3] * 768],
            metadatas=[
                {"source_file": "file_a.txt", "page_number": 1, "content_type": "text"},
                {"source_file": "file_a.txt", "page_number": 1, "content_type": "text"},
                {"source_file": "file_b.txt", "page_number": 1, "content_type": "text"},
            ],
            ids=["id1", "id2", "id3"],
        )

        result = get_indexed_files()

        assert set(result.keys()) == {"file_a.txt", "file_b.txt"}
        assert len(result["file_a.txt"]) == 2
        assert len(result["file_b.txt"]) == 1

    def test_chunk_record_has_expected_keys(self, clean_collection):
        clean_collection.add(
            documents=["hello world"],
            embeddings=[[0.1] * 768],
            metadatas=[{"source_file": "doc.txt", "page_number": 1, "content_type": "text"}],
            ids=["id-x"],
        )

        result = get_indexed_files()
        chunk = result["doc.txt"][0]

        assert "document" in chunk
        assert "metadata" in chunk
        assert "id" in chunk
        assert chunk["document"] == "hello world"
        assert chunk["metadata"]["source_file"] == "doc.txt"

    def test_skips_chunks_with_missing_source_file(self, clean_collection):
        clean_collection.add(
            documents=["orphan chunk"],
            embeddings=[[0.1] * 768],
            metadatas=[{"page_number": 1, "content_type": "text"}],  # no source_file
            ids=["orphan-id"],
        )

        result = get_indexed_files()
        assert result == {}
```

> **Note on `clean_collection` fixture:** Check if it already exists in `test_vector_store.py`. If it does, reuse it. If not, add this fixture at the top of the test file (or in a `conftest.py`):
>
> ```python
> import pytest
> import chromadb
> from unittest.mock import patch
>
> @pytest.fixture
> def clean_collection(tmp_path):
>     """Provides a fresh in-memory ChromaDB collection, patching the module-level one."""
>     client = chromadb.EphemeralClient()
>     col = client.get_or_create_collection("test_collection")
>     with patch("vector_store.collection", col):
>         yield col
> ```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ai-chat && python -m pytest test_vector_store.py::TestGetIndexedFiles -v
```

Expected: `FAILED` — `ImportError: cannot import name 'get_indexed_files'`

- [ ] **Step 3: Implement `get_indexed_files()` in `vector_store.py`**

Add after the `query_vector_store` function:

```python
def get_indexed_files() -> dict[str, list[dict[str, Any]]]:
    """Returns all indexed files grouped by source_file.

    Each value is a list of chunk records with keys: document, metadata, id.
    Chunks missing the source_file metadata key are silently skipped.
    """
    result = collection.get(include=["documents", "metadatas"])

    documents: list[str] = result.get("documents") or []
    metadatas: list[dict[str, Any]] = result.get("metadatas") or []
    ids: list[str] = result.get("ids") or []

    file_index: dict[str, list[dict[str, Any]]] = {}
    for doc, meta, doc_id in zip(documents, metadatas, ids):
        source = meta.get("source_file")
        if not source:
            continue
        file_index.setdefault(source, []).append(
            {"document": doc, "metadata": meta, "id": doc_id}
        )

    return file_index
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd ai-chat && python -m pytest test_vector_store.py::TestGetIndexedFiles -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add ai-chat/vector_store.py ai-chat/test_vector_store.py
git commit -m "feat(vector-store): add get_indexed_files()"
```

---

## Task 2: Add `delete_file()` to `vector_store.py`

**Files:**
- Modify: `ai-chat/vector_store.py`
- Test: `ai-chat/test_vector_store.py`

- [ ] **Step 1: Write the failing tests**

Add to `test_vector_store.py`:

```python
class TestDeleteFile:
    """Tests for delete_file()."""

    def test_deletes_all_chunks_for_source_file(self, clean_collection):
        # Arrange
        clean_collection.add(
            documents=["chunk a", "chunk b", "chunk c"],
            embeddings=[[0.1] * 768, [0.2] * 768, [0.3] * 768],
            metadatas=[
                {"source_file": "target.pdf", "page_number": 1, "content_type": "text"},
                {"source_file": "target.pdf", "page_number": 2, "content_type": "text"},
                {"source_file": "other.txt", "page_number": 1, "content_type": "text"},
            ],
            ids=["t1", "t2", "o1"],
        )

        deleted = delete_file("target.pdf")

        assert deleted == 2
        remaining = clean_collection.get(where={"source_file": "target.pdf"})
        assert len(remaining["ids"]) == 0
        # other.txt untouched
        other = clean_collection.get(where={"source_file": "other.txt"})
        assert len(other["ids"]) == 1

    def test_returns_zero_when_file_not_found(self, clean_collection):
        deleted = delete_file("nonexistent.pdf")
        assert deleted == 0

    def test_returns_correct_count_for_single_chunk_file(self, clean_collection):
        clean_collection.add(
            documents=["only chunk"],
            embeddings=[[0.1] * 768],
            metadatas=[{"source_file": "solo.txt", "page_number": 1, "content_type": "text"}],
            ids=["s1"],
        )

        deleted = delete_file("solo.txt")
        assert deleted == 1
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ai-chat && python -m pytest test_vector_store.py::TestDeleteFile -v
```

Expected: `FAILED` — `ImportError: cannot import name 'delete_file'`

- [ ] **Step 3: Implement `delete_file()` in `vector_store.py`**

Add after `get_indexed_files()`:

```python
def delete_file(source_file: str) -> int:
    """Deletes all chunks for the given source_file from ChromaDB.

    Returns the number of chunks deleted.
    """
    existing = collection.get(where={"source_file": source_file})
    ids_to_delete: list[str] = existing.get("ids") or []
    if not ids_to_delete:
        return 0
    collection.delete(ids=ids_to_delete)
    return len(ids_to_delete)
```

> **Why `get` then `delete`?** ChromaDB's `delete(where=...)` does not return a count. We fetch IDs first so we can return an accurate count and also use `delete(ids=...)` which is the most reliable deletion method.

- [ ] **Step 4: Run all vector store tests**

```bash
cd ai-chat && python -m pytest test_vector_store.py -v
```

Expected: All existing tests + `TestDeleteFile` pass. No regressions.

- [ ] **Step 5: Commit**

```bash
git add ai-chat/vector_store.py ai-chat/test_vector_store.py
git commit -m "feat(vector-store): add delete_file()"
```

---

## Task 3: Add the file list section to the sidebar in `main.py`

**Files:**
- Modify: `ai-chat/main.py`

- [ ] **Step 1: Add session state initialization**

In `main.py`, find the existing session state block for `messages` (around line 79):

```python
if 'messages' not in st.session_state:
    st.session_state.messages = []
```

Add the two new keys **above** that block, near the top of the module body (after `eval_client = init_telemetry()`):

```python
if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None

if 'pending_delete' not in st.session_state:
    st.session_state.pending_delete = None
```

- [ ] **Step 2: Import the new vector_store functions**

Find the existing import line in `main.py`:

```python
from vector_store import collection
```

Replace it with:

```python
from vector_store import collection, delete_file, get_indexed_files
```

- [ ] **Step 3: Build the file index and render the file list in the sidebar**

In `main.py`, locate the `with st.sidebar:` block (around line 36). It currently ends after the "Process & Ingest" button logic. Add the file list **immediately after** the closing of that `if uploaded_file is not None and st.button(...)` block, still inside `with st.sidebar:`:

```python
    # ── File Manager ──────────────────────────────────────────────
    st.divider()

    try:
        file_index = get_indexed_files()
    except Exception as e:
        st.warning(f'Could not load file index: {e}')
        file_index = {}

    file_names = sorted(file_index.keys())
    st.subheader(f'📋 Uploaded Files ({len(file_names)})')

    if not file_names:
        st.caption('No files ingested yet. Upload a document above.')
    else:
        for fname in file_names:
            chunks = file_index[fname]
            icon = '🖼' if fname.lower().split('.')[-1] in ('png', 'jpg', 'jpeg', 'webp') else '📄'

            col_name, col_view, col_del = st.columns([5, 1, 1])
            with col_name:
                st.caption(f'{icon} {fname}  ·  {len(chunks)} chunks')
            with col_view:
                if st.button('👁', key=f'view_{fname}', help='View details'):
                    st.session_state.selected_file = fname
                    st.session_state.pending_delete = None
                    st.rerun()
            with col_del:
                if st.button('🗑', key=f'del_{fname}', help='Delete file'):
                    st.session_state.pending_delete = fname
                    st.rerun()

            # Inline delete confirmation
            if st.session_state.pending_delete == fname:
                st.warning(
                    f'⚠ Delete **{fname}** and all {len(chunks)} chunks from the index?'
                )
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button('Confirm Delete', key=f'confirm_{fname}', type='primary'):
                        try:
                            delete_file(fname)
                            if st.session_state.selected_file == fname:
                                st.session_state.selected_file = None
                            st.session_state.pending_delete = None
                            st.rerun()
                        except Exception as e:
                            st.error(f'Delete failed: {e}')
                with cancel_col:
                    if st.button('Cancel', key=f'cancel_{fname}'):
                        st.session_state.pending_delete = None
                        st.rerun()
```

- [ ] **Step 4: Smoke test — launch the app and verify the file list renders**

```bash
cd ai-chat && streamlit run main.py
```

Open http://localhost:8501. The sidebar should show:
- The existing upload widget at the top
- A divider
- `📋 Uploaded Files (N)` with 👁 and 🗑 buttons per file
- Clicking 🗑 shows the inline confirmation; clicking Cancel dismisses it

- [ ] **Step 5: Commit**

```bash
git add ai-chat/main.py
git commit -m "feat(ai-chat): add file list section to sidebar"
```

---

## Task 4: Add the tabbed detail panel to `main.py`

**Files:**
- Modify: `ai-chat/main.py`

The detail panel renders to the right of the chat area when `st.session_state.selected_file` is set. We achieve this by wrapping the existing tab1/tab2 content in a conditional column layout.

- [ ] **Step 1: Wrap the existing chat/eval tabs in a column layout**

In `main.py`, find the line:

```python
tab1, tab2 = st.tabs(['💬 Chat', '🧪 Evaluation'])
```

Replace the layout so it becomes:

```python
if st.session_state.selected_file and st.session_state.selected_file in file_index:
    main_col, detail_col = st.columns([2, 1])
else:
    main_col = st.container()
    detail_col = None

with main_col:
    tab1, tab2 = st.tabs(['💬 Chat', '🧪 Evaluation'])
```

> The rest of the `with tab1:` and `with tab2:` blocks remain **unchanged** — they're still indented under `tab1`/`tab2`, not under `main_col`. Only the `st.tabs(...)` call moves inside `with main_col:`.

- [ ] **Step 2: Render the detail panel**

After the closing of the `with main_col:` block, add:

```python
if detail_col is not None:
    selected = st.session_state.selected_file
    chunks = file_index.get(selected, [])

    with detail_col:
        # Header
        ext = selected.rsplit('.', 1)[-1].upper() if '.' in selected else 'FILE'
        icon = '🖼' if ext.lower() in ('png', 'jpg', 'jpeg', 'webp') else '📄'
        total_chars = sum(len(c['document']) for c in chunks)

        close_col, _ = st.columns([1, 4])
        with close_col:
            if st.button('✕ Close', key='detail_close'):
                st.session_state.selected_file = None
                st.rerun()

        st.markdown(f'### {icon} {selected}')
        st.caption(f'{ext} · {len(chunks)} chunks · {total_chars:,} chars')

        # Tabs
        ov_tab, ch_tab, raw_tab = st.tabs([
            'Overview',
            f'Chunks ({len(chunks)})',
            'Raw Content',
        ])

        with ov_tab:
            _render_overview_tab(selected, chunks, ext)

        with ch_tab:
            _render_chunks_tab(chunks)

        with raw_tab:
            _render_raw_tab(chunks)
```

- [ ] **Step 3: Add the three tab helper functions**

Add these three functions to `main.py` **before** the `st.set_page_config(...)` line is reached at render time — place them after the imports and before `eval_client = init_telemetry()`:

```python
from collections import Counter


def _render_overview_tab(filename: str, chunks: list[dict], ext: str) -> None:
    """Renders the Overview tab of the file detail panel."""
    pages = sorted({c['metadata'].get('page_number', 1) for c in chunks})
    content_types = Counter(c['metadata'].get('content_type', 'text') for c in chunks)

    st.markdown(f'**File type:** `{ext}`')
    st.markdown(f'**Total chunks:** `{len(chunks)}`')
    st.markdown(f'**Total characters:** `{sum(len(c["document"]) for c in chunks):,}`')
    st.markdown(f'**Pages spanned:** `{len(pages)}` (pages {pages[0]}–{pages[-1]})' if len(pages) > 1 else f'**Page:** `{pages[0]}`')
    st.markdown('**Content types:**')
    for ctype, count in content_types.most_common():
        st.markdown(f'- `{ctype}` × {count}')
    st.markdown('**Chunk size:** `1000` chars')
    st.markdown('**Chunk overlap:** `100` chars')


def _render_chunks_tab(chunks: list[dict]) -> None:
    """Renders the Chunks tab of the file detail panel."""
    sorted_chunks = sorted(
        chunks,
        key=lambda c: (c['metadata'].get('page_number', 0),),
    )
    for i, chunk in enumerate(sorted_chunks, start=1):
        meta = chunk['metadata']
        page = meta.get('page_number', '?')
        ctype = meta.get('content_type', 'text')
        char_count = len(chunk['document'])
        preview = chunk['document'][:200]
        full = chunk['document']

        with st.expander(
            f'Chunk {i} · `{ctype}` · Page {page} · {char_count:,} chars — {preview[:60]}…'
        ):
            st.code(full, language='markdown')


def _render_raw_tab(chunks: list[dict]) -> None:
    """Renders the Raw Content tab of the file detail panel."""
    sorted_chunks = sorted(
        chunks,
        key=lambda c: (c['metadata'].get('page_number', 0),),
    )
    raw = '\n\n---\n\n'.join(c['document'] for c in sorted_chunks)
    st.code(raw, language='markdown')
```

- [ ] **Step 4: Smoke test — open the detail panel**

```bash
cd ai-chat && streamlit run main.py
```

1. Upload and ingest a file (or use one already in ChromaDB).
2. Click 👁 on a file in the sidebar.
3. Verify the detail panel opens to the right showing Overview / Chunks / Raw Content tabs.
4. Switch between tabs and confirm content renders.
5. Click ✕ Close — panel should disappear and layout returns to full-width.

- [ ] **Step 5: Commit**

```bash
git add ai-chat/main.py
git commit -m "feat(ai-chat): add tabbed file detail panel"
```

---

## Task 5: End-to-end delete flow verification

**Files:** No code changes — verification only.

- [ ] **Step 1: Test the full delete flow**

With the app running:
1. Ingest at least two files so both appear in the file list.
2. Open the detail panel for file A (👁).
3. Click 🗑 on file A — confirm inline warning appears.
4. Click **Confirm Delete** — verify:
   - The file disappears from the sidebar list.
   - The detail panel closes (because `selected_file` was cleared).
   - The remaining file still appears.
5. Verify in ChromaDB that the chunks are gone:

```bash
cd ai-chat && python -c "
from vector_store import collection
r = collection.get(where={'source_file': 'YOUR_FILE_NAME'})
print('Remaining chunks:', len(r['ids']))
"
```

Expected: `Remaining chunks: 0`

- [ ] **Step 2: Test the cancel flow**

Click 🗑 on a file, then click **Cancel** — confirm no deletion occurs and the confirmation row disappears.

- [ ] **Step 3: Run the full test suite**

```bash
cd ai-chat && python -m pytest test_vector_store.py -v
```

Expected: All tests pass with no regressions.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "test(ai-chat): verify file manager end-to-end delete flow"
```
