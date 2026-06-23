# Design Spec: AI Chat File Manager Sidebar

**Date:** 2026-06-23
**Status:** Approved
**Scope:** `ai-chat/main.py` — Streamlit sidebar enhancement

---

## 1. Overview

Add a **file manager panel** to the existing left sidebar in `ai-chat/main.py`. Users can see every file ingested into ChromaDB, inspect its content and chunking details, and delete it entirely.

The feature has two visual components:

1. **File list** — a persistent section in the sidebar showing all ingested files with action buttons.
2. **Detail panel** — a right-hand panel that opens when the user clicks 👁 on a file, showing three tabs: Overview, Chunks, and Raw Content.

---

## 2. Architecture

### 2.1 Data Source

The file list is **derived entirely from ChromaDB** — no additional database or persistent store is introduced. On every page render, the app queries `collection.get()` and groups results by `source_file` metadata to build the file index.

```
ChromaDB collection
  └── all documents
        └── grouped by metadata["source_file"]
              └── → list of FileRecord(name, chunk_count, chunks[])
```

This means:
- Files survive page refresh and app restarts (ChromaDB is persistent).
- The list is always consistent with what's actually indexed.
- No session-state file tracking is needed.

### 2.2 New Helper: `get_indexed_files()`

A new function in `vector_store.py` returns all files and their chunks:

```python
def get_indexed_files() -> dict[str, list[dict]]:
    """Returns {source_file: [chunk_records]} for all documents in ChromaDB."""
```

Each chunk record contains:
- `document` — the raw chunk text
- `metadata` — `source_file`, `page_number`, `content_type`, optionally `asset_path`
- `id` — ChromaDB document ID

### 2.3 Delete: `delete_file(source_file: str)`

A new function in `vector_store.py` that removes all chunks for a given `source_file`:

```python
def delete_file(source_file: str) -> int:
    """Deletes all chunks for source_file from ChromaDB. Returns deleted count."""
```

Uses `collection.delete(where={"source_file": source_file})`. This matches the existing deletion pattern already used in the evaluation tab.

### 2.4 Streamlit Session State

Two new keys track UI state:

| Key | Type | Purpose |
|-----|------|---------|
| `selected_file` | `str \| None` | Which file's detail panel is open |
| `pending_delete` | `str \| None` | File awaiting delete confirmation |

---

## 3. Components

### 3.1 Sidebar: Upload Section (unchanged)

The existing upload widget and "Process & Ingest" button remain exactly as-is.

### 3.2 Sidebar: File List

Rendered **below** the upload section, separated by a `st.divider()`.

**Header:** `📋 Uploaded Files (N)` — N is the count of distinct source files.

**Per-file row** (using `st.columns`):
- File icon (📄 for text/PDF, 🖼 for images) + filename (truncated if long)
- Chunk count badge: `N chunks`
- 👁 button → sets `selected_file` to this file's name
- 🗑 button → sets `pending_delete` to this file's name

**Delete confirmation** (shown inline below the file row when `pending_delete` matches):
- Warning message: `⚠ Delete {name} and all N chunks from the index?`
- Two buttons: `Confirm Delete` (red) and `Cancel`
- On confirm: calls `delete_file()`, clears `pending_delete`, clears `selected_file` if it was the deleted file, calls `st.rerun()`.

**Empty state:** If no files are indexed, show a muted message: *"No files ingested yet. Upload a document above."*

### 3.3 Detail Panel (Right Column)

Implemented using `st.set_page_config(layout="wide")` (already set). When `selected_file` is set, the main content area is split into two columns: `main_col, detail_col = st.columns([2, 1])`. The detail panel lives in `detail_col`. When no file is selected, a single full-width column is used.

**Panel header:**
- File name (with icon)
- File type badge + total chunk count + total character count
- Close button (✕) → sets `selected_file = None`, reruns

**Three tabs** via `st.tabs(["Overview", "Chunks (N)", "Raw Content"])`:

#### Tab 1 — Overview
A metadata summary table:

| Field | Value |
|-------|-------|
| File type | PDF / TXT / Image |
| Total chunks | N |
| Total characters | sum of `len(chunk)` across all chunks |
| Pages spanned | distinct `page_number` values |
| Content types | breakdown: text ×N, table ×N, image_caption ×N |
| Chunk size | 1000 chars (static display, matches splitter config) |
| Chunk overlap | 100 chars (static display) |

#### Tab 2 — Chunks (N)
Scrollable list of all chunks for this file. Each chunk card shows:
- Chunk index (1-based)
- Content type badge (text / table / image_caption)
- Page number
- Character count
- Text preview (first 200 chars), with a `st.expander` to reveal the full chunk text

#### Tab 3 — Raw Content
The full extracted markdown text for this file, displayed in `st.code(language="markdown")`. Reconstructed by joining all chunk documents ordered by `page_number` then chunk index.

> **Note:** The raw content is reconstructed from stored chunks, not the original file (which is not retained after ingestion). Minor overlap artifacts from chunking may appear.

---

## 4. Data Flow

```
Page render
  └── get_indexed_files()
        └── collection.get(include=["documents","metadatas"])
              └── group by source_file
                    └── build file_index: dict[str, list[dict]]

Sidebar renders file_index
  └── user clicks 👁 on "report.pdf"
        └── st.session_state.selected_file = "report.pdf"
              └── st.rerun()
                    └── detail panel renders file_index["report.pdf"]

User clicks 🗑 on "notes.txt"
  └── st.session_state.pending_delete = "notes.txt"
        └── confirmation row renders
              └── user clicks "Confirm Delete"
                    └── delete_file("notes.txt")
                          └── collection.delete(where={"source_file": "notes.txt"})
                                └── st.rerun()
```

---

## 5. Error Handling

| Scenario | Handling |
|----------|----------|
| ChromaDB unreachable on `get_indexed_files()` | Catch exception, show `st.warning("Could not load file index.")`, render empty list |
| Delete fails mid-operation | Catch exception, show `st.error(f"Delete failed: {e}")`, do not rerun |
| `selected_file` no longer exists after delete | Detail panel silently closes (file not found in `file_index`) |
| Chunk missing `source_file` metadata | Skip that chunk — it won't appear in the file list |

---

## 6. Files Changed

| File | Change |
|------|--------|
| `ai-chat/vector_store.py` | Add `get_indexed_files()` and `delete_file()` |
| `ai-chat/main.py` | Add file list section to sidebar; add detail panel column; add session state keys |

No new files. No new dependencies.

---

## 7. Out of Scope

- Per-chunk deletion (whole-file only)
- Re-ingesting / replacing a file
- Sorting or filtering the file list
- Storing original file bytes for re-download
