# Multi-Modal RAG Pipeline & Evaluation Chat

This directory contains a complete, robust, multi-modal Retrieval-Augmented Generation (RAG) pipeline and benchmarking system. It leverages the Google GenAI SDK, ChromaDB, and PyMuPDF to parse documents (including PDFs with image captioning), index them, retrieve context, generate responses, and measure quality against reference datasets.

## Features

- **Document Ingestion & Parsing**: Parses plain text (`.txt`), PDF (`.pdf`) documents, and standalone images (`.png`, `.jpg`, `.jpeg`, `.webp`).
- **Structured OCR & Captioning**: Utilizes Gemini structured output JSON schemas to perform both high-fidelity OCR and visual captioning in a single request.
- **Scanned PDF OCR & Hybrid Parsing**: Identifies scanned/empty pages in PDFs dynamically and runs page-level OCR via Gemini structured outputs to extract text and captions, preserving PDF formatting.
- **Vector Search & Storage**: Stores document chunks and metadata in a persistent ChromaDB instance.
- **Agentic RAG Execution**: Employs Gemini Function Calling to dynamically route queries. The LLM decides whether to perform document retrieval or answer directly. Includes a forced-retrieval fallback to support evaluation and benchmarking pipelines.
- **Benchmarking Suite**: Evaluates precision, recall, and semantic answer quality (LLM-as-a-judge) on test cases, complete with API rate limit protection.

---

## Setup & Installation

### Prerequisites

* Python 3.12 or higher
* [uv](https://github.com/astral-sh/uv) (recommended package manager) or standard `pip`

### 1. Install Dependencies

Sync and install the project requirements:
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file inside the `ai-chat` directory (or export variables in your shell):
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Running the Application

### Running the Chat Interface
To launch the interactive terminal chat:
```bash
python main.py
```

### Running the Benchmark Suite
To run the evaluation benchmark on the Paul Graham Essay dataset:
```bash
python benchmark.py
```
This will run the first 5 test cases from `benchmark_data/test_cases.json` by default (safe for free-tier API quotas) and output a markdown summary table.

### Running Unit Tests
To run all unit tests for the pipeline:
```bash
pytest
```

---

## Documentation

For deep technical details, refer to:
* [Architecture Documentation](docs/ARCHITECTURE.md) - Deep dive into parsing, embedding, vector store, and generation logic.
* [Benchmarking Documentation](docs/BENCHMARK.md) - Details on the dataset, metrics calculation, and latest benchmark results.
