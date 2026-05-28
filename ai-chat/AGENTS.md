# EvalPlatform: Multimodal RAG Agent
> The reference AI application built to ingest user documents, perform multimodal Retrieval-Augmented Generation, and stream rich telemetry to the EvalPlatform.

## 1. Agent Principles

| Principle | Technical Implication |
| :--- | :--- |
| **Telemetry-First Design** | Every interaction is explicitly wrapped with the `evalplatform_sdk` to ensure `input_text`, `output_text`, `retrieved_context`, and `artifacts` are captured flawlessly. |
| **Native Multimodality** | The agent does not just read text; it parses images and PDFs natively, treating them as first-class `artifacts` in the runtime state. |
| **Transparent Grounding** | All retrieved chunks used to formulate an answer are exposed in the telemetry `metadata`, allowing the backend AI-Judges to score for hallucination and faithfulness. |
| **Decoupled Architecture** | The UI (Next.js) handles streaming and file uploads, while the Engine (Python/FastAPI) handles vector search, LLM orchestration, and SDK logging. |

---

## 2. Domain Lexicon

### RAG Entities
* **`Document Artifact`**: An uploaded file (Image, PDF, or TXT) parsed and attached to the user's prompt.
* **`Vector Store`**: The local database (e.g., ChromaDB) holding embedded document chunks for semantic retrieval.
* **`Retrieved Context`**: The specific text chunks extracted from the Vector Store that are injected into the LLM's system prompt to ground the answer.

### Telemetry Counterparts
* **`Trace Wrapper`**: The `@capture_trace` decorator from the `evalplatform_sdk` used to time the RAG pipeline and package the `RuntimeState`.
* **`State Metadata`**: The exact location where this agent stores the `retrieved_context` so the backend's Extractor Registry can find it.

---

## 3. System Architecture & Tech Stack

* **Frontend UI:** `next` & `react` (Chat interface with drag-and-drop file support).
* **UI AI Integration:** `ai` (Vercel AI SDK `useChat` hook for seamless streaming).
* **RAG Backend:** `fastapi` (Python backend required to utilize the `evalplatform_sdk`).
* **LLM Orchestration:** `langchain` or `llama-index` (Document loaders, chunking, and retrieval).
* **Multimodal Model:** `google-genai` (Gemini 1.5 Pro/Flash for native long-context PDF and image understanding).
* **Vector Database:** `chromadb` (Local, ephemeral vector store for the MVP).

---

## 4. Agent Directory Structure

```text
ai-chat/
├── package.json            # Next.js UI dependencies
├── pyproject.toml          # Python RAG engine dependencies
├── src/
│   ├── app/                # Next.js Frontend
│   │   ├── page.tsx        # Main Chat UI
│   │   └── components/     # File upload & message components
│   └── engine/             # Python RAG Backend
│       ├── main.py         # FastAPI streaming endpoint
│       ├── retriever.py    # ChromaDB & Document Loaders (PDF/Image)
│       └── generator.py    # Gemini integration wrapped with evalplatform_sdk
```
