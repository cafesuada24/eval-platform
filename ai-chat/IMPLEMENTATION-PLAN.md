# Multimodal RAG Agent Implementation Plan

**Objective:** Build a Next.js chat interface backed by a Python FastAPI RAG engine that processes PDFs/Images and streams telemetry to the EvalPlatform via the SDK.

## Phase 1: Frontend Chat & File Upload (Next.js)
**Goal:** Build the user interface capable of handling text and multimodal file attachments.

1.  **Initialize Chat UI (`src/app/page.tsx`)**:
    * Implement the Vercel AI SDK `useChat` hook pointing to your local FastAPI backend (e.g., `http://localhost:8000/api/chat`).
    * Build the message list to render user queries, agent responses, and thumbnails of uploaded files.
2.  **Multimodal Input Component**:
    * Implement a drag-and-drop zone or file picker accepting `.pdf`, `.png`, `.jpg`, and `.txt`.
    * Convert selected files to `base64` before appending them to the message payload sent to the backend.

---

## Phase 2: RAG Engine & Vector Store (Python)
**Goal:** Process incoming files, chunk them, embed them, and set up the semantic retrieval pipeline.

1.  **Document Ingestion (`src/engine/retriever.py`)**:
    * Initialize an in-memory `chromadb` client.
    * Write `process_upload(file_bytes, mime_type)`:
      * **For PDFs/Text:** Use LangChain/LlamaIndex document loaders to parse text, chunk it (e.g., 1000 tokens), embed using a standard embedding model, and store in ChromaDB.
      * **For Images:** If the model supports native image inputs (like Gemini), pass the `base64` string directly; otherwise, run a lightweight OCR pass and embed the extracted text.
2.  **Semantic Search**:
    * Write `retrieve_context(query: str) -> List[str]`: Perform a similarity search on the vector store and return the top-K matching text chunks.

---

## Phase 3: Telemetry Integration & Generation
**Goal:** Marry the RAG pipeline with the `evalplatform_sdk` to ensure every chat turn is fully observable.

1.  **The Generation Wrapper (`src/engine/generator.py`)**:
    * Import `EvalClient` and `@capture_trace` (or the `trace` context manager) from the locally installed `evalplatform_sdk`.
    * Write the main generation function:
      ```python
      from evalplatform_sdk.helpers import trace
      from evalplatform_sdk.models import Artifact
      
      async def generate_rag_response(user_message: str, files: list):
          with trace(trace_id=generate_uuid()) as t:
              # 1. Retrieve Context
              retrieved_chunks = retrieve_context(user_message)
              
              # 2. Package SDK Metadata (CRITICAL for the Backend Extractor)
              t.set_metadata({"retrieved_context": retrieved_chunks})
              
              # 3. Package Artifacts
              for file in files:
                  t.add_artifact(Artifact(type=file.mime_type, content=file.base64))
              
              # 4. Construct Prompt & Call LLM (Gemini)
              system_prompt = f"Answer based on context: {retrieved_chunks}"
              llm_response = await call_gemini(system_prompt, user_message, files)
              
              # 5. Finalize Trace
              t.set_input(user_message)
              t.set_output(llm_response.text)
              
              return llm_response.stream
      ```

---

## Phase 4: The FastAPI Streaming Endpoint
**Goal:** Expose the generator to the Next.js frontend via Server-Sent Events (SSE).

1.  **API Router (`src/engine/main.py`)**:
    * Initialize a FastAPI application with CORS enabled for the Next.js frontend.
    * Create `POST /api/chat`.
    * Accept the Vercel AI SDK standard payload (`{"messages": [...]}`).
    * Extract the latest user message and any attached files.
    * Pass them to `generate_rag_response`.
    * Return the LLM response using FastAPI's `StreamingResponse`, ensuring compatibility with the Vercel AI SDK text stream format.
