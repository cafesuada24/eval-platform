# Technical Design Specification: Minimalist Multi-Modal RAG Pipeline Upgrade

## 1. Objective & Philosophy
### 1.1 Objective
Upgrade the existing RAG pipeline to a robust, highly efficient Multi-Modal Retrieval-Augmented Generation (RAG) pipeline designed for text, complex PDFs (with dense formatting, tables, and embedded images), and standalone image assets.

### 1.2 Core Philosophy: "Đại đạo chí giản" (Extreme Simplicity)
* **Unified target representation:** Convert all multi-modal ingestion formats (PDFs, images) into a single Markdown-based text representation (combining text, tables, and inline semantic captions).
* **Flat database model:** Use a single, unified ChromaDB collection mapped to raw assets via clean metadata routing, avoiding redundant multi-vector databases.

---

## 2. Technical Stack & Dependencies
* **Language:** Python 3.12+
* **Primary Parser:** `pymupdf4llm` (for PDF-to-Markdown conversion and image extraction)
* **Fallback Parser:** `pypdf` (for text-only extraction)
* **LLM & Vision Provider:** Google GenAI SDK (`google-genai`)
  * *Vision / Ingestion Model:* `gemini-3.1-flash-lite`
  * *Ultimate Synthesis / Generation Model:* `gemini-3.1-flash-lite`
* **Embedding Engine:** Google Gemini Embedding 2 (`gemini-embedding-2`) via `google-genai`
* **Vector Database:** ChromaDB

---

## 3. Architecture & File Modularization
The codebase will be separated into four single-responsibility modules:

1. **`parser.py` (Ingestion & Extraction):**
   - Extracts PDF pages to raw Markdown and extracts embedded images to a dedicated directory: `assets/extracted_images`.
   - Formats extracted images with the naming pattern: `<pdf_basename>_page_<page_num>_img_<index>.<ext>`.
   - Sends extracted/standalone images to `gemini-3.1-flash-lite` to generate semantic captions.
   - Replaces/appends image references in markdown text with generated captions.
2. **`embedder.py` (Embedding Vector Generation):**
   - Calls the Google GenAI SDK to generate embedding vectors using `gemini-embedding-2` in batches.
   - Implements backoff/retry handling for Google API rate limits.
3. **`vector_store.py` (ChromaDB Management):**
   - Interface for initializing and writing/querying the `ai_chat_docs` ChromaDB collection using pre-computed embeddings.
4. **`rag_engine.py` (RAG Orchestration & Multi-Modal Synthesis):**
   - Coordinates vector search, context hydration (loading PIL images if `content_type == "image_caption"`), and calls the final synthesis model.

### Metadata Schema
Every chunk stored in the vector database will adhere to this schema:
```json
{
  "source_file": "string (original filename)",
  "page_number": "int (1-indexed page number)",
  "content_type": "text | table | image_caption",
  "asset_path": "string (local path to raw image if content_type is image_caption, else empty)"
}
```

---

## 4. Detailed Data Flow

### 4.1 Ingestion Phase (Approach 1: Unified Markdown + Inline/Standalone Ingestion)
1. **Document Conversion:**
   - Run `pymupdf4llm.to_markdown(pdf_path, write_images=True, image_path="assets/extracted_images")`.
2. **Semantic Transmutation:**
   - Scan `assets/extracted_images/` for images extracted from the PDF.
   - For each image, call `gemini-3.1-flash-lite` using the following system prompt:
     ```text
     Analyze this image within the context of a technical document repository. Provide a highly detailed, dense semantic description, captioning all visual charts, figures, text within images, and structural meaning. Output purely descriptive text.
     ```
   - In the page's markdown text, locate the image reference tag (e.g., `![](path/to/img)`) and append/replace it with the generated caption:
     `![](path/to/img)\n\n**Image Caption:** {caption}`
3. **Chunking & Storage:**
   - Use `MarkdownTextSplitter` (chunk size: 1000, overlap: 100) to split the unified markdown.
   - Map metadata dynamically to each chunk (identifying tables by `|` grid layout and captions by image patterns).
   - For each extracted image, create a standalone chunk containing only the semantic caption, labeled as `content_type: "image_caption"` and mapping its `asset_path`.
   - Batch vectorize all text chunks using `gemini-embedding-2`.
   - Store the chunks, vectors, and metadata in ChromaDB.

### 4.2 Retrieval & Context Hydration Phase
1. **Query Vectorization:** Convert the user's query into a vector using `gemini-embedding-2`.
2. **Vector Query:** Query ChromaDB for top-K matching chunks.
3. **Context Hydration:**
   - Initialize `multimodal_inputs = []` and a `context_text_list = []`.
   - Loop through retrieved chunks:
     - Append chunk text to `context_text_list`.
     - If the chunk metadata `content_type == "image_caption"`, load the image at `asset_path` using PIL and append it to `multimodal_inputs`.
4. **Synthesis:**
   - Build the generation prompt:
     ```text
     Answer the user's question based ONLY on the provided context, including any attached figures or tables.
     
     Context:
     {context}
     ```
   - Pass PIL images and prompt to the synthesis engine (`gemini-3.1-flash-lite`):
     `client.models.generate_content(model="gemini-3.1-flash-lite", contents=[*multimodal_inputs, prompt])`

---

## 5. Telemetry & Tracing Integration
Every operation will be explicitly traced using the `evalplatform-sdk`:
* **Parser (`parser.py`):** Wrapped in `state.track_file_processed()`. Logs the filename, processor name `pymupdf4llm_gemini`, and the resulting markdown output content.
* **Retrieval (`rag_engine.py`):** Wrapped in `state.track_retrieval()`. Logs the query and calls `rt.add_chunk()` to record each retrieved chunk's source document, content, and similarity distance.
* **Generation (`rag_engine.py`):** Wrapped in `state.track_generation()`. Logs model provider information, user input, token counts (`prompt_token_count` and `candidates_token_count`), and the generated response.

---

## 6. Resilience & Error Handling
* **API Rate Limits:** Wrap all Google GenAI calls (embeddings and completion) in an exponential backoff with retry mechanism.
* **Missing Images:** If `asset_path` cannot be read during context hydration, log a warning and fallback to using the text semantic caption alone (avoiding synthesis crash).
* **Parser Fallback:** If `pymupdf4llm` crashes on a corrupt file, catch the exception, fall back to page-by-page `pypdf` text extraction, log the issue, and continue text ingestion.

---

## 7. Phased Rollout Plan
* **Phase 1: Environment & Parsing:** Setup dependencies, implement `parser.py`, and verify PDF extraction to Markdown + image saving.
* **Phase 2: Semantic Image Transmutation:** Integrate `gemini-3.1-flash-lite` image captioning and inline markdown replacement.
* **Phase 3: Embedding & Storage:** Implement `embedder.py` and `vector_store.py` with batch embedding and ChromaDB collection writing.
* **Phase 4: RAG Loop & Telemetry:** Connect RAG retrieval, context hydration, multimodal synthesis, and update Streamlit UI, `eval.py`, and tests.
