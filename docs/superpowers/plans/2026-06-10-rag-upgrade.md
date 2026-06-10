# Minimalist Multi-Modal RAG Pipeline Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing RAG pipeline to a robust, highly efficient Multi-Modal RAG pipeline that converts PDFs to Markdown (using `pymupdf4llm`), captions extracted images using `gemini-3.1-flash-lite`, and indexes text and images into ChromaDB using manual `gemini-embedding-2` vectorization.

**Architecture:** The pipeline is split into four clean modules (`parser.py`, `embedder.py`, `vector_store.py`, `rag_engine.py`) to parse, embed, store, and run RAG. During retrieval, metadata routing is checked, and any `image_caption` content types trigger loading the raw image file as PIL inputs to the final generation step.

**Tech Stack:** Python 3.12+, `pymupdf4llm`, `pypdf`, `chromadb`, `google-genai`, `pillow`, `langchain-text-splitters`, `streamlit`.

---

## File Structure Map
* **New Files:**
  - `ai-chat/parser.py`: Ingestion, image extraction, and semantic caption inline replacement.
  - `ai-chat/embedder.py`: Batch embedding generation via Google GenAI SDK with retries.
  - `ai-chat/vector_store.py`: ChromaDB collection management (with pre-computed vectors).
  - `ai-chat/rag_engine.py`: Retrieval, context hydration (PIL image loading), and synthesis.
  - `ai-chat/test_parser.py`: Unit tests for parser.
  - `ai-chat/test_embedder.py`: Unit tests for embedding.
  - `ai-chat/test_vector_store.py`: Unit tests for ChromaDB storage.
  - `ai-chat/test_rag_engine.py`: Unit tests for RAG retrieval and answer generation.
* **Modified Files:**
  - `ai-chat/pyproject.toml`: Addition of dependencies (`pymupdf4llm`).
  - `ai-chat/main.py`: Streamlit frontend integration.
  - `ai-chat/eval.py`: Evaluation pipeline integration.
  - `ai-chat/test_app.py`: Verification tests.

---

### Task 1: Environment & Dependency Setup

**Files:**
* Modify: `ai-chat/pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**
  Add `pymupdf4llm` to the dependencies array.
  ```toml
  # In pyproject.toml dependencies:
  dependencies = [
      "chromadb>=1.5.9",
      "easyocr>=1.7.2",
      "evalplatform-sdk",
      "google-genai>=2.6.0",
      "langchain-text-splitters>=1.1.2",
      "pillow>=12.2.0",
      "pypdf>=6.12.2",
      "pymupdf4llm>=0.0.17",
      "python-dotenv>=1.2.2",
      "streamlit>=1.58.0",
  ]
  ```

- [ ] **Step 2: Sync dependencies**
  Run uv sync or pip install to install the newly added dependency.
  Run: `uv pip install pymupdf4llm` or `pip install pymupdf4llm`
  Expected output: Success installation of `pymupdf4llm`.

- [ ] **Step 3: Commit**
  ```bash
  git add pyproject.toml
  git commit -m "build: add pymupdf4llm dependency for PDF parsing"
  ```

---

### Task 2: Ingestion & Extraction Module (`parser.py`)

**Files:**
* Create: `ai-chat/parser.py`
* Create: `ai-chat/test_parser.py`

- [ ] **Step 1: Write unit tests for parser**
  Create `ai-chat/test_parser.py` to verify basic PDF parsing, TXT parsing, and page-by-page mapping.
  ```python
  import os
  import pytest
  from parser import extract_text_from_txt, extract_text_from_pdf_fallback

  def test_extract_text_from_txt(tmp_path):
      txt_file = tmp_path / "test.txt"
      txt_file.write_text("Hello, this is a test.", encoding="utf-8")
      result = extract_text_from_txt(str(txt_file))
      assert "Hello, this is a test." in result

  def test_extract_text_from_pdf_fallback(tmp_path):
      # We just test the fallback behavior on a missing/invalid file
      with pytest.raises(Exception):
          extract_text_from_pdf_fallback("non_existent_file.pdf")
  ```

- [ ] **Step 2: Run tests to verify failure**
  Run: `pytest test_parser.py`
  Expected: FAIL with `ModuleNotFoundError: No module named 'parser'`

- [ ] **Step 3: Implement parser.py**
  Create `ai-chat/parser.py` containing the text extraction and fallback parsing logic.
  ```python
  import os
  import re
  from pathlib import Path
  from pypdf import PdfReader

  def extract_text_from_txt(file_path: str) -> str:
      with open(file_path, "r", encoding="utf-8") as f:
          return f.read()

  def extract_text_from_pdf_fallback(file_path: str) -> tuple[str, list[dict]]:
      """Fallback parser extracting text page-by-page using pypdf."""
      pdf_reader = PdfReader(file_path)
      unified_markdown_parts = []
      for page_idx, page in enumerate(pdf_reader.pages):
          page_num = page_idx + 1
          page_text = page.extract_text() or ""
          page_marker = f"\n\n<!-- PAGE_{page_num} -->\n\n"
          unified_markdown_parts.append(page_marker + page_text)
      return "".join(unified_markdown_parts), []
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest test_parser.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add parser.py test_parser.py
  git commit -m "feat: add parser module with text and pypdf fallback extraction"
  ```

---

### Task 3: PDF parsing with image extraction & captioning

**Files:**
* Modify: `ai-chat/parser.py`
* Modify: `ai-chat/test_parser.py`

- [ ] **Step 1: Write test for PDF image extraction & captioning**
  Extend `ai-chat/test_parser.py` to define the function signature and expected return structure.
  ```python
  import os
  from parser import ingest_pdf_document

  def test_ingest_pdf_document_signature():
      assert callable(ingest_pdf_document)
  ```

- [ ] **Step 2: Run test to verify failure**
  Run: `pytest test_parser.py`
  Expected: FAIL with import error for `ingest_pdf_document`.

- [ ] **Step 3: Implement ingest_pdf_document and caption generation**
  Modify `ai-chat/parser.py` to add `pymupdf4llm` parsing, local image extraction, and semantic caption generation.
  ```python
  import pymupdf4llm
  from PIL import Image
  from google import genai
  import time

  def generate_image_caption(image_path: str) -> str:
      """Generates a dense semantic description of an image using gemini-3.1-flash-lite."""
      if not os.path.exists(image_path):
          raise FileNotFoundError(f"Image not found at {image_path}")
      
      # Retries for Gemini API limits
      max_retries = 3
      delay = 2
      last_err = None
      
      for attempt in range(max_retries):
          try:
              client = genai.Client()
              pil_image = Image.open(image_path)
              prompt = (
                  "Analyze this image within the context of a technical document repository. "
                  "Provide a highly detailed, dense semantic description, captioning all visual "
                  "charts, figures, text within images, and structural meaning. Output purely descriptive text."
              )
              response = client.models.generate_content(
                  model="gemini-3.1-flash-lite",
                  contents=[pil_image, prompt]
              )
              return response.text or ""
          except Exception as e:
              last_err = e
              time.sleep(delay)
              delay *= 2
      raise last_err

  def ingest_pdf_document(file_path: str) -> tuple[str, list[dict]]:
      """
      Converts PDF to Markdown using pymupdf4llm, extracts images, generates semantic
      captions for them, and injects them back inline into the markdown text.
      """
      pdf_basename = os.path.splitext(os.path.basename(file_path))[0]
      img_dir = Path("assets/extracted_images")
      img_dir.mkdir(parents=True, exist_ok=True)
      
      try:
          pages = pymupdf4llm.to_markdown(
              file_path,
              write_images=True,
              image_path=str(img_dir),
              page_chunks=True
          )
      except Exception as e:
          print(f"pymupdf4llm failed: {e}. Falling back to pypdf.")
          return extract_text_from_pdf_fallback(file_path)

      extracted_images_info = []
      unified_markdown_parts = []
      
      for page in pages:
          page_num = page['metadata'].get('page', 0) + 1
          text = page['text']
          
          # Find image references written by pymupdf4llm e.g., ![](image-page0-0.png)
          img_refs = re.findall(r'!\[\]\(([^)]+)\)', text)
          
          for idx, img_ref in enumerate(img_refs):
              img_filename = os.path.basename(img_ref)
              old_path = img_dir / img_filename
              
              if old_path.exists():
                  ext = old_path.suffix.lower()
                  new_filename = f"{pdf_basename}_page_{page_num}_img_{idx}{ext}"
                  new_path = img_dir / new_filename
                  
                  # Rename file
                  old_path.rename(new_path)
                  
                  # Generate semantic caption
                  try:
                      caption = generate_image_caption(str(new_path))
                  except Exception as caption_err:
                      print(f"Failed to generate caption for {new_path}: {caption_err}")
                      caption = "[Image caption generation failed]"
                  
                  # Update text: replace image tag with new path & inline caption reference
                  inline_ref = f"![]({new_path})\n\n**Image Caption:** {caption}"
                  text = text.replace(f"![]({img_ref})", inline_ref)
                  
                  extracted_images_info.append({
                      "asset_path": str(new_path.absolute()),
                      "page_number": page_num,
                      "caption": caption
                  })
          
          page_marker = f"\n\n<!-- PAGE_{page_num} -->\n\n"
          unified_markdown_parts.append(page_marker + text)
          
      return "".join(unified_markdown_parts), extracted_images_info
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest test_parser.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add parser.py test_parser.py
  git commit -m "feat: implement image extraction, caption generation, and inline replacement in parser"
  ```

---

### Task 4: Embedding Module (`embedder.py`)

**Files:**
* Create: `ai-chat/embedder.py`
* Create: `ai-chat/test_embedder.py`

- [ ] **Step 1: Write test for embedding module**
  Create `ai-chat/test_embedder.py`.
  ```python
  import pytest
  from unittest.mock import MagicMock, patch

  @patch("embedder.genai.Client")
  def test_generate_embeddings(mock_client_class):
      mock_client = MagicMock()
      mock_embedding = MagicMock()
      mock_embedding.values = [0.1, 0.2, 0.3]
      mock_client.models.embed_content.return_value.embeddings = [mock_embedding]
      mock_client_class.return_value = mock_client
      
      from embedder import generate_embeddings
      res = generate_embeddings(["hello"])
      assert len(res) == 1
      assert res[0] == [0.1, 0.2, 0.3]
  ```

- [ ] **Step 2: Run tests to verify failure**
  Run: `pytest test_embedder.py`
  Expected: FAIL with `ModuleNotFoundError: No module named 'embedder'`

- [ ] **Step 3: Implement embedder.py**
  Create `ai-chat/embedder.py` to interact with Google GenAI SDK.
  ```python
  import time
  from google import genai

  def generate_embeddings(texts: list[str]) -> list[list[float]]:
      """Generates embedding vectors for a list of texts using gemini-embedding-2."""
      if not texts:
          return []
          
      client = genai.Client()
      max_retries = 3
      delay = 2
      last_err = None
      
      for attempt in range(max_retries):
          try:
              response = client.models.embed_content(
                  model="gemini-embedding-2",
                  contents=texts
              )
              return [embedding.values for embedding in response.embeddings]
          except Exception as e:
              last_err = e
              time.sleep(delay)
              delay *= 2
      raise last_err
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest test_embedder.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add embedder.py test_embedder.py
  git commit -m "feat: implement embedder module with gemini-embedding-2 batch generation"
  ```

---

### Task 5: ChromaDB Interface Module (`vector_store.py`)

**Files:**
* Create: `ai-chat/vector_store.py`
* Create: `ai-chat/test_vector_store.py`

- [ ] **Step 1: Write test for ChromaDB storage**
  Create `ai-chat/test_vector_store.py`.
  ```python
  import pytest
  from unittest.mock import MagicMock
  from vector_store import add_chunks_to_db

  def test_add_chunks_to_db_empty():
      # Should return safely without executing collection operations
      add_chunks_to_db([], [], [], "test.pdf")
  ```

- [ ] **Step 2: Run tests to verify failure**
  Run: `pytest test_vector_store.py`
  Expected: FAIL with `ModuleNotFoundError: No module named 'vector_store'`

- [ ] **Step 3: Implement vector_store.py**
  Create `ai-chat/vector_store.py`.
  ```python
  import os
  import uuid
  import chromadb

  DB_DIR = os.path.join(os.path.dirname(__file__), 'db')
  chroma_client = chromadb.PersistentClient(path=DB_DIR)
  collection = chroma_client.get_or_create_collection(name='ai_chat_docs')

  def add_chunks_to_db(chunks: list[str], embeddings: list[list[float]], metadatas: list[dict], source: str):
      """Inserts chunk strings, embedding vectors, and metadata schema into ChromaDB."""
      if not chunks:
          return
      ids = [str(uuid.uuid4()) for _ in chunks]
      collection.add(
          documents=chunks,
          embeddings=embeddings,
          metadatas=metadatas,
          ids=ids
      )

  def query_vector_store(query_vector: list[float], n_results: int = 3) -> dict:
      """Queries ChromaDB using a pre-computed query vector."""
      if collection.count() == 0:
          return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
      
      return collection.query(
          query_embeddings=[query_vector],
          n_results=min(n_results, collection.count())
      )
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest test_vector_store.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add vector_store.py test_vector_store.py
  git commit -m "feat: implement vector_store module with manual embeddings insertion and query interface"
  ```

---

### Task 6: RAG Engine & Context Hydration (`rag_engine.py`)

**Files:**
* Create: `ai-chat/rag_engine.py`
* Create: `ai-chat/test_rag_engine.py`

- [ ] **Step 1: Write test for rag_engine**
  Create `ai-chat/test_rag_engine.py`.
  ```python
  import pytest
  from unittest.mock import MagicMock

  def test_rag_engine_import():
      import rag_engine
      assert hasattr(rag_engine, "retrieve_context")
  ```

- [ ] **Step 2: Run tests to verify failure**
  Run: `pytest test_rag_engine.py`
  Expected: FAIL with `ModuleNotFoundError: No module named 'rag_engine'`

- [ ] **Step 3: Implement rag_engine.py**
  Create `ai-chat/rag_engine.py` using `evalplatform-sdk` telemetry integration.
  ```python
  import os
  from PIL import Image
  from google import genai
  import time
  from evalplatform_sdk.models import RuntimeState
  from embedder import generate_embeddings
  from vector_store import query_vector_store

  def retrieve_context(state: RuntimeState, query: str, n_results: int = 3) -> tuple[str, list[str]]:
      """
      Retrieves matching chunks from ChromaDB, hydrates images if they correspond to
      image captions, and returns (context_text, image_paths).
      """
      with state.track_retrieval() as rt:
          rt.query(query)
          
          # Vectorize query
          query_embeddings = generate_embeddings([query])
          if not query_embeddings:
              return "", []
          
          results = query_vector_store(query_embeddings[0], n_results)
          
          docs = results.get("documents", [[]])[0] or []
          metadatas = results.get("metadatas", [[]])[0] or []
          distances = results.get("distances", [[]])[0] or []
          
          image_paths = []
          context_parts = []
          
          for i, doc in enumerate(docs):
              meta = metadatas[i] if i < len(metadatas) else {}
              dist = distances[i] if i < len(distances) else 1.0
              source = meta.get("source_file", "")
              
              rt.add_chunk(document=source, content=doc, confidence=float(dist))
              context_parts.append(doc)
              
              if meta.get("content_type") == "image_caption":
                  path = meta.get("asset_path")
                  if path and os.path.exists(path):
                      image_paths.append(path)
                      
          return "\n\n".join(context_parts), image_paths

  def generate_answer(state: RuntimeState, query: str, context: str, image_paths: list[str]) -> str:
      """Generates multimodal answers combining context text and loaded raw PIL images."""
      model_name = 'gemini-3.1-flash-lite'
      client = genai.Client()
      
      prompt = f"""You are a helpful AI assistant. Answer the user's question based ONLY on the provided context, including any attached figures or tables.
  If you cannot answer the question based on the context, say "I don't have enough information to answer that."

  Context:
  {context}

  Question:
  {query}
  """
      contents = []
      for path in image_paths:
          try:
              img = Image.open(path)
              contents.append(img)
          except Exception as e:
              print(f"Skipping loading image {path}: {e}")
              
      contents.append(prompt)
      
      with state.track_generation() as gen_tracker:
          gen_tracker.model_info(provider='google', model_name=model_name)
          gen_tracker.user_input(query)
          
          max_retries = 3
          delay = 2
          last_err = None
          
          for attempt in range(max_retries):
              try:
                  response = client.models.generate_content(model=model_name, contents=contents)
                  answer = response.text or ""
                  break
              except Exception as e:
                  last_err = e
                  time.sleep(delay)
                  delay *= 2
          else:
              raise last_err
              
          if response.usage_metadata:
              gen_tracker.token_usage(
                  input_tokens=response.usage_metadata.prompt_token_count,
                  output_tokens=response.usage_metadata.candidates_token_count,
              )
          gen_tracker.output_text(answer)
          
      return answer
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest test_rag_engine.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add rag_engine.py test_rag_engine.py
  git commit -m "feat: implement RAG engine with context hydration and multimodal synthesis"
  ```

---

### Task 7: Integrate Modular Ingestion in code

**Files:**
* Modify: `ai-chat/parser.py` (adding main ingest pipeline orchestration)
* Modify: `ai-chat/main.py`
* Modify: `ai-chat/eval.py`
* Modify: `ai-chat/test_app.py`

- [ ] **Step 1: Write ingestion pipeline orchestrator**
  Update `ai-chat/parser.py` to add `ingest_file` function replacing the old `ingest_file` from `ingest.py`.
  ```python
  from langchain_text_splitters import MarkdownTextSplitter
  from embedder import generate_embeddings
  from vector_store import add_chunks_to_db

  def ingest_file(file_path: str) -> int:
      """
      Orchestrates file reading, image caption generation, chunking, 
      embedding, and insertion to ChromaDB. Returns the number of chunks added.
      """
      ext = os.path.splitext(file_path)[-1].lower()
      filename = os.path.basename(file_path)
      
      extracted_images_info = []
      
      if ext == ".txt":
          markdown_text = extract_text_from_txt(file_path)
      elif ext in [".png", ".jpg", ".jpeg"]:
          # Standalone image ingestion
          img_dir = Path("assets/extracted_images")
          img_dir.mkdir(parents=True, exist_ok=True)
          new_filename = f"standalone_{uuid.uuid4().hex}_{filename}"
          new_path = img_dir / new_filename
          
          # Copy to assets/extracted_images
          with open(file_path, "rb") as src, open(new_path, "wb") as dst:
              dst.write(src.read())
              
          caption = generate_image_caption(str(new_path))
          markdown_text = f"**Standalone Image Caption ({filename}):** {caption}"
          extracted_images_info.append({
              "asset_path": str(new_path.absolute()),
              "page_number": 1,
              "caption": caption
          })
      elif ext == ".pdf":
          markdown_text, extracted_images_info = ingest_pdf_document(file_path)
      else:
          raise ValueError(f"Unsupported file type: {ext}")
          
      # Split markdown using MarkdownTextSplitter
      splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=100)
      text_chunks = splitter.split_text(markdown_text)
      
      metadatas = []
      chunks_to_insert = []
      
      # Prepare chunks and metadata for normal markdown chunks
      for chunk in text_chunks:
          # Determine page number by matching comments <!-- PAGE_(\d+) -->
          page_match = re.search(r'<!-- PAGE_(\d+) -->', chunk)
          page_num = int(page_match.group(1)) if page_match else 1
          
          content_type = "text"
          if "|" in chunk:
              content_type = "table"
              
          metadatas.append({
              "source_file": filename,
              "page_number": page_num,
              "content_type": content_type,
              "asset_path": ""
          })
          chunks_to_insert.append(chunk)
          
      # Prepare chunks and metadata for standalone image caption chunks
      for img_info in extracted_images_info:
          chunks_to_insert.append(img_info["caption"])
          metadatas.append({
              "source_file": filename,
              "page_number": img_info["page_number"],
              "content_type": "image_caption",
              "asset_path": img_info["asset_path"]
          })
          
      # Generate embeddings for all chunks in a batch
      embeddings = generate_embeddings(chunks_to_insert)
      
      # Add to DB
      add_chunks_to_db(chunks_to_insert, embeddings, metadatas, filename)
      return len(chunks_to_insert)
  ```

- [ ] **Step 2: Update main.py UI integration**
  Modify imports and business logic in `ai-chat/main.py` to use our new parser, vector_store, and rag_engine modules.
  Lines 9-11 should be replaced:
  ```python
  # REPLACE:
  # from ingest import extract_text_from_image, ingest_file
  # from langchain_text_splitters import RecursiveCharacterTextSplitter
  # from rag import add_chunks_to_db, collection, generate_answer, retrieve_context
  
  # WITH:
  from parser import ingest_file, generate_image_caption
  from vector_store import collection
  import rag_engine
  ```
  Lines 57-62 should be replaced:
  ```python
  # REPLACE:
  # chunks = ingest_file(tmp_path)
  # add_chunks_to_db(chunks, source=uploaded_file.name)
  # st.success(f'Successfully ingested {len(chunks)} chunks from {uploaded_file.name}')
  
  # WITH:
  num_chunks = ingest_file(tmp_path)
  st.success(f'Successfully ingested {num_chunks} chunks from {uploaded_file.name}')
  ```
  Lines 92-98 should be replaced:
  ```python
  # REPLACE:
  # with trace() as state:
  #     context = retrieve_context(state, prompt)
  #     answer = generate_answer(state, prompt, context)
  
  # WITH:
  with trace() as state:
      context, image_paths = rag_engine.retrieve_context(state, prompt)
      answer = rag_engine.generate_answer(state, prompt, context, image_paths)
  ```
  Lines 190-216 should be replaced:
  ```python
  # REPLACE OCR download and parse loop with updated logic
  # WITH:
  with state.track_file_processed() as file_tracker:
      file_tracker.file_info(
          file_name=filename, processor='ocr',
      )
      extracted_text = generate_image_caption(tmp_path)
      file_tracker.content(extracted_text)

  # Chunk and index into ChromaDB using parser ingestion
  num_chunks = ingest_file(tmp_path)
  st.write(f'  └─ Indexed {num_chunks} chunks into vector DB.')
  ```
  Line 213-219:
  ```python
  # REPLACE:
  # context = retrieve_context(state, query)
  # answer = generate_answer(state, query, context)
  
  # WITH:
  context, image_paths = rag_engine.retrieve_context(state, query)
  answer = rag_engine.generate_answer(state, query, context, image_paths)
  ```
  Line 222:
  ```python
  # REPLACE:
  # collection.delete(where={'source': filename})
  
  # WITH:
  collection.delete(where={'source_file': filename})
  ```

- [ ] **Step 3: Update eval.py integration**
  Modify imports and execution loop in `ai-chat/eval.py`.
  ```python
  # REPLACE:
  # from rag import generate_answer, retrieve_context
  
  # WITH:
  import rag_engine
  ```
  Modify RAG loop inside `eval.py`:
  ```python
  # REPLACE:
  # context = retrieve_context(state, query)
  # answer = generate_answer(state, query, context)
  
  # WITH:
  context, image_paths = rag_engine.retrieve_context(state, query)
  answer = rag_engine.generate_answer(state, query, context, image_paths)
  ```

- [ ] **Step 4: Update test_app.py integration**
  Modify imports and logic in `ai-chat/test_app.py`.
  Replace imports and execution block with correct references.
  ```python
  from parser import ingest_file
  import rag_engine
  from vector_store import collection
  ```
  And query sequence:
  ```python
  num_chunks = ingest_file("dummy.txt")
  print(f"Ingested {num_chunks} chunks.")
  
  with trace() as state:
      print("Querying ChromaDB...")
      query = "When was the AI Chat application built?"
      context, image_paths = rag_engine.retrieve_context(state, query)
      print(f"Retrieved context:\n{context}")
      
      if "GEMINI_API_KEY" in os.environ or "GOOGLE_API_KEY" in os.environ:
          answer = rag_engine.generate_answer(state, query, context, image_paths)
          print(f"Answer: {answer}")
  ```

- [ ] **Step 5: Run tests**
  Run: `pytest`
  Expected: PASS

- [ ] **Step 6: Commit**
  ```bash
  git add main.py eval.py test_app.py parser.py
  git commit -m "feat: integrate modular multi-modal RAG ingestion and retrieval in app, eval, and test runner"
  ```

---

## Phase X: Verification & Cleanup

- [ ] **Step 1: Run security scans**
  Run: `python .agents/scripts/checklist.py .`
  Expected: Security scans and lint checks pass cleanly.

- [ ] **Step 2: Verify application end-to-end**
  Run: `python test_app.py`
  Expected: Successful completion.

- [ ] **Step 3: Remove old files**
  Wait, do we have old unused files? Yes, `ingest.py` and `rag.py` are now fully replaced by `parser.py`, `embedder.py`, `vector_store.py`, `rag_engine.py`.
  Clean up unused imports/variables and remove `ingest.py` and `rag.py` since their contents are migrated.
  Run: `git rm ingest.py rag.py`

- [ ] **Step 4: Final commit**
  ```bash
  git commit -m "cleanup: remove obsolete single-file ingest and rag scripts"
  ```

- [ ] **Step 5: Write Phase X completion marker**
  Add Phase X completion summary to this file.
