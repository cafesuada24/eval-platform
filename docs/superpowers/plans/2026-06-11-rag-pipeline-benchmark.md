# Multi-Modal RAG Pipeline Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained local benchmarking suite that measures retrieval/generation performance, token metrics, and semantic accuracy of the Multi-Modal RAG pipeline under free-tier Gemini API constraints.

**Architecture:** An isolated CLI tool executes the benchmark. It clears the local database, ingests multi-modal test files, queries the RAG pipeline using test cases, evaluates RAG citations (Precision/Recall), grades answer correctness using Gemini-as-a-judge, enforces a 4-second cooldown to stay under free-tier API limits, and outputs a formatted Markdown report.

**Tech Stack:** Python 3.12+, `pytest`, `google-genai`, `chromadb`, `jinja2` (or built-in formatting).

---

### Task 1: Setup Dataset & Test Cases

**Files:**
- Create: `ai-chat/benchmark_data/test_cases.json`
- Create: `ai-chat/benchmark_data/sample_text.txt`
- Create: `ai-chat/benchmark_data/sample_doc.pdf` (empty placeholder)
- Create: `ai-chat/benchmark_data/sample_image.png` (empty placeholder)

- [ ] **Step 1: Create sample text document**
  Write a short text file containing technical requirements.
  Path: `ai-chat/benchmark_data/sample_text.txt`
  Content:
  ```text
  The Multi-Modal RAG system requires Python 3.12+ and 16GB of RAM.
  The primary API key should be stored in the GOOGLE_API_KEY environment variable.
  ```

- [ ] **Step 2: Create sample PDF and Image placeholders**
  We will create dummy files for local test runs.
  Path: `ai-chat/benchmark_data/sample_doc.pdf`
  Path: `ai-chat/benchmark_data/sample_image.png`
  Content: Write simple dummy bytes for placeholder files.

- [ ] **Step 3: Create benchmark test cases**
  Write a test case configuration specifying RAG queries, target sources, target content types, and references.
  Path: `ai-chat/benchmark_data/test_cases.json`
  Content:
  ```json
  [
    {
      "id": "TC_001",
      "query": "What does the text document list as the primary system requirements?",
      "expected_sources": ["sample_text.txt"],
      "expected_content_types": ["text"],
      "reference_answer": "The primary requirements are Python 3.12+ and 16GB RAM.",
      "category": "text_retrieval"
    }
  ]
  ```

- [ ] **Step 4: Commit**
  ```bash
  git add ai-chat/benchmark_data/
  git commit -m "test: add benchmark dataset and test cases"
  ```

---

### Task 2: Implement Metric Helper Functions (TDD)

**Files:**
- Create: `ai-chat/test_benchmark.py`
- Modify: `ai-chat/benchmark.py` (creating helper functions)

- [ ] **Step 1: Write failing tests for helper functions**
  Create unit tests for Precision/Recall calculation and semantic score parsing.
  Path: `ai-chat/test_benchmark.py`
  Code:
  ```python
  import pytest
  from benchmark import calculate_precision_recall, parse_semantic_score

  def test_calculate_precision_recall() -> None:
      retrieved_metadatas = [
          {"source_file": "sample_text.txt", "content_type": "text"},
          {"source_file": "other.pdf", "content_type": "table"}
      ]
      expected_sources = ["sample_text.txt"]
      expected_content_types = ["text"]
      
      precision, recall = calculate_precision_recall(
          retrieved_metadatas, expected_sources, expected_content_types
      )
      assert precision == 0.5
      assert recall == 1.0

  def test_parse_semantic_score_valid() -> None:
      assert parse_semantic_score(" 0.85 \n") == 0.85
      assert parse_semantic_score("Score: 0.9") == 0.9
      assert parse_semantic_score("invalid") == 0.0
  ```

- [ ] **Step 2: Run tests to verify they fail**
  Run: `pytest test_benchmark.py`
  Expected: FAIL with `ModuleNotFoundError: No module named 'benchmark'`

- [ ] **Step 3: Implement minimal code in benchmark.py**
  Create helper functions to calculate Precision/Recall and parse floats.
  Path: `ai-chat/benchmark.py`
  Code:
  ```python
  import re
  from typing import Any

  def calculate_precision_recall(
      retrieved_metadatas: list[dict[str, Any]],
      expected_sources: list[str],
      expected_content_types: list[str]
  ) -> tuple[float, float]:
      """Calculates citation Precision and Recall for RAG chunk retrieval."""
      if not retrieved_metadatas:
          return 0.0, 0.0
      
      relevant_retrieved = 0
      for meta in retrieved_metadatas:
          src = meta.get("source_file", "")
          ctype = meta.get("content_type", "")
          if src in expected_sources and ctype in expected_content_types:
              relevant_retrieved += 1
              
      precision = relevant_retrieved / len(retrieved_metadatas)
      
      # For recall, expected size is product of sources and types
      total_expected = len(expected_sources) * len(expected_content_types)
      recall = relevant_retrieved / total_expected if total_expected > 0 else 0.0
      return precision, min(recall, 1.0)

  def parse_semantic_score(text: str) -> float:
      """Extracts a float score from the model judge response."""
      match = re.search(r"(\d+\.\d+|\d+)", text)
      if match:
          val = float(match.group(1))
          return min(max(val, 0.0), 1.0)
      return 0.0
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest test_benchmark.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add ai-chat/test_benchmark.py ai-chat/benchmark.py
  git commit -m "feat: implement benchmark helper metrics with unit tests"
  ```

---

### Task 3: Ingestion & Telemetry Runner setup

**Files:**
- Modify: `ai-chat/benchmark.py`
- Modify: `ai-chat/test_benchmark.py`

- [ ] **Step 1: Write test for API call retry decorator**
  Ensure that api calls wrap retry logic correctly.
  Path: `ai-chat/test_benchmark.py`
  Code:
  ```python
  from unittest.mock import MagicMock, patch
  from benchmark import retry_api_call

  @patch("benchmark.time.sleep")
  def test_retry_api_call_succeeds(mock_sleep: MagicMock) -> None:
      mock_func = MagicMock()
      mock_func.side_effect = [Exception("Limit"), "Success"]
      
      result = retry_api_call(mock_func)
      assert result == "Success"
      assert mock_func.call_count == 2
      mock_sleep.assert_called_once_with(2.0)
  ```

- [ ] **Step 2: Run tests to verify it fails**
  Run: `pytest test_benchmark.py::test_retry_api_call_succeeds`
  Expected: FAIL (missing `retry_api_call`)

- [ ] **Step 3: Implement retry decorator in benchmark.py**
  Path: `ai-chat/benchmark.py`
  Code:
  ```python
  import time
  from typing import Callable, TypeVar

  T = TypeVar('T')

  def retry_api_call(func: Callable[[], T], max_retries: int = 5, initial_delay: float = 2.0) -> T:
      """Executes API function call with exponential backoff retry."""
      delay = initial_delay
      for attempt in range(max_retries + 1):
          try:
              return func()
          except Exception as e:
              if attempt == max_retries:
                  raise e
              time.sleep(delay)
              delay *= 2.0
      raise RuntimeError("Unreachable")
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest test_benchmark.py`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add ai-chat/benchmark.py ai-chat/test_benchmark.py
  git commit -m "feat: add robust api retry logic to benchmark"
  ```

---

### Task 4: Complete Main Benchmark Runner Logic

**Files:**
- Modify: `ai-chat/benchmark.py`

- [ ] **Step 1: Implement clear database and ingestion tracking**
  Path: `ai-chat/benchmark.py`
  Code: Add imports, database reset, ingestion loops, context retrieval, Gemini-as-a-judge scorer, and markdown formatter.
  ```python
  import os
  import json
  from google import genai
  from parser import ingest_file
  from vector_store import collection
  from rag_engine import retrieve_context, generate_answer
  from evalplatform_sdk.helpers import trace
  from evalplatform_sdk.client import EvalClient

  def clear_database() -> None:
      """Deletes all entries from local ChromaDB collection."""
      count = collection.count()
      if count > 0:
          collection.delete(where={})
          print(f"Cleared {count} existing chunks from vector store.")

  def evaluate_response_quality(client: genai.Client, query: str, candidate: str, reference: str) -> float:
      """Uses Gemini as a judge to evaluate answer correctness."""
      prompt = f"""Compare the candidate response to the ground-truth reference answer for correctness and completeness. Rate the correctness on a scale from 0.0 (completely incorrect) to 1.0 (perfectly correct and complete). Output only a floating-point number.

  Reference Answer:
  {reference}

  Candidate Response:
  {candidate}
  """
      def call() -> str:
          res = client.models.generate_content(
              model="gemini-3.1-flash-lite",
              contents=prompt
          )
          return res.text or "0.0"
          
      response_text = retry_api_call(call)
      return parse_semantic_score(response_text)

  def run_benchmark() -> None:
      """Main entrypoint coordinating RAG ingestion, retrieval, and scoring."""
      clear_database()
      
      data_dir = "benchmark_data"
      test_cases_path = os.path.join(data_dir, "test_cases.json")
      if not os.path.exists(test_cases_path):
          print(f"Test cases file not found at {test_cases_path}")
          return
          
      with open(test_cases_path) as f:
          test_cases = json.load(f)
          
      # Ingest files
      for filename in os.listdir(data_dir):
          if filename == "test_cases.json":
              continue
          file_path = os.path.join(data_dir, filename)
          start_time = time.time()
          chunks = ingest_file(file_path)
          elapsed = (time.time() - start_time) * 1000
          print(f"Ingested {filename}: {chunks} chunks in {elapsed:.1f}ms")
          time.sleep(4.0)  # Cooldown
          
      client = genai.Client()
      results = []
      
      # Mock SDK client for runtime context
      eval_client = EvalClient(api_key="test", base_url="http://test")
      
      for case in test_cases:
          print(f"Running Case {case['id']}: {case['query']}")
          
          # 1. Retrieval
          start_time = time.time()
          with trace() as state:
              context, image_paths = retrieve_context(state, case["query"])
              retrieval_ms = (time.time() - start_time) * 1000
              
              # Extract retrieved metadata
              # We fetch from collection to get matched metadata
              # For simplicity, we search for source_file in metadata
              query_embeddings = client.models.embed_content(
                  model="gemini-embedding-2",
                  contents=[case["query"]]  # type: ignore[arg-type]
              )
              matched = collection.query(
                  query_embeddings=[query_embeddings.embeddings[0].values],  # type: ignore[arg-type]
                  n_results=3
              )
              metadatas = matched.get("metadatas", [[]])[0] or []
              
              precision, recall = calculate_precision_recall(
                  metadatas, case["expected_sources"], case["expected_content_types"]
              )
              
              # 2. Generation
              start_time = time.time()
              answer = generate_answer(state, case["query"], context, image_paths)
              gen_ms = (time.time() - start_time) * 1000
              
          time.sleep(4.0)  # Cooldown
          
          # 3. Judge evaluation
          score = evaluate_response_quality(client, case["query"], answer, case["reference_answer"])
          print(f"  Score: {score:.2f} | Retrieval: {retrieval_ms:.1f}ms | Gen: {gen_ms:.1f}ms")
          
          results.append({
              "id": case["id"],
              "query": case["query"],
              "retrieval_ms": retrieval_ms,
              "gen_ms": gen_ms,
              "precision": precision,
              "recall": recall,
              "semantic_score": score
          })
          time.sleep(4.0)  # Cooldown
          
      # Print markdown report
      print("\n" + "="*60)
      print("📊 RAG BENCHMARK RESULTS")
      print("="*60)
      print("| ID | Query | Retrieval Latency | Gen Latency | Precision | Recall | Semantic Score |")
      print("|----|-------|-------------------|-------------|-----------|--------|----------------|")
      for r in results:
          print(f"| {r['id']} | {r['query'][:30]}... | {r['retrieval_ms']:.1f}ms | {r['gen_ms']:.1f}ms | {r['precision']:.2f} | {r['recall']:.2f} | {r['semantic_score']:.2f} |")
          
      # Dump JSON
      with open("benchmark_results.json", "w") as f:
          json.dump(results, f, indent=2)
          
  if __name__ == "__main__":
      run_benchmark()
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add ai-chat/benchmark.py
  git commit -m "feat: complete RAG benchmark runner logic and execution harness"
  ```

---

### Task 5: End-to-End Execution Check

**Files:**
- None (verification run)

- [ ] **Step 1: Execute test suite**
  Run `pytest` to make sure unit tests pass.
  Run: `pytest`

- [ ] **Step 2: Run benchmark script**
  Run: `python benchmark.py`
  Expected: Clear outputs detailing ingestion, case execution, and final score summary.

- [ ] **Step 3: Verify JSON results output**
  Confirm file `benchmark_results.json` exists and matches the schema.
  Run: `cat benchmark_results.json`
