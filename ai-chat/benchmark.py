"""Benchmark helper functions for multi-modal RAG metrics."""

import json
import logging
import os
import re
import time
from typing import Callable, TypeVar

from embedder import generate_embeddings
from evalplatform_sdk.helpers import trace
from google import genai
from parser import ingest_file
from rag_engine import generate_answer, retrieve_context
from vector_store import collection, query_vector_store

T = TypeVar("T")

logger = logging.getLogger(__name__)


def calculate_precision_recall(
    retrieved_metadatas: list[dict],
    expected_sources: list[str],
    expected_content_types: list[str],
) -> tuple[float, float]:
    """Calculate precision and recall for retrieved chunk metadatas.

    A retrieved metadata is relevant if its source_file matches expected_sources
    and its content_type matches expected_content_types.
    """
    if not retrieved_metadatas:
        return 0.0, 0.0

    relevant_count = 0
    for meta in retrieved_metadatas:
        source = meta.get("source_file")
        content_type = meta.get("content_type")
        if source in expected_sources and content_type in expected_content_types:
            relevant_count += 1

    precision = relevant_count / len(retrieved_metadatas)

    denominator = len(expected_sources) * len(expected_content_types)
    if denominator == 0:
        recall = 0.0
    else:
        recall = min(relevant_count / denominator, 1.0)

    return precision, recall


def parse_semantic_score(text: str) -> float:
    """Parse semantic score from text.

    Extracts the first floating-point or integer number in the text,
    caps it between 0.0 and 1.0. If no match is found, logs a warning and returns 0.0.
    """
    match = re.search(r"(\d+\.\d+|\d+)", text)
    if not match:
        logger.warning(f"Could not parse semantic score from LLM response: {text}")
        return 0.0

    val = float(match.group(1))
    return min(max(val, 0.0), 1.0)


def retry_api_call(
    func: Callable[[], T], max_retries: int = 5, initial_delay: float = 2.0
) -> T:
    """Execute func with exponential backoff retries on Exception.

    Retries up to max_retries times. If all retries fail, propagates the last exception.
    """
    delay = initial_delay
    for attempt in range(1, max_retries + 2):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries + 1:
                logger.error(f"API call failed after {max_retries + 1} attempts: {e}")
                raise
            logger.warning(
                f"API call failed (attempt {attempt}/{max_retries + 1}): {e}. "
                f"Retrying in {delay}s..."
            )
            time.sleep(delay)
            delay *= 2.0


def clear_database() -> None:
    """Clear all records from the ChromaDB collection if it contains any items."""
    count = collection.count()
    if count > 0:
        try:
            collection.delete(where={})
        except ValueError:
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)
        logger.info(f"Cleared {count} items from database.")
    else:
        logger.info("Database is already empty.")


def evaluate_response_quality(candidate: str, reference: str) -> float:
    """Evaluate response quality comparing candidate answer to reference answer.

    Prompts gemini-3.1-flash-lite to score correctness/quality on a scale of 0.0 to 1.0,
    and returns the parsed float.
    """
    client = genai.Client()
    prompt = (
        "You are an expert evaluator. Compare the candidate answer to the reference answer.\n"
        "Rate the semantic correctness/quality of the candidate answer relative to the reference answer "
        "on a scale from 0.0 to 1.0.\n"
        "Output only the score (a number between 0.0 and 1.0).\n\n"
        f"Reference Answer:\n{reference}\n\n"
        f"Candidate Answer:\n{candidate}\n"
    )

    def api_call() -> str:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
        )
        return response.text or ""

    response_text = retry_api_call(api_call)
    return parse_semantic_score(response_text)


def run_benchmark(data_dir: str | None = None) -> list[dict]:
    """Runs the benchmark pipeline on the test cases.

    Clears the DB, ingests data files, runs RAG on test cases, and scores quality.
    """
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "benchmark_data")

    # 1. Clear database
    clear_database()

    # 2. Ingest files
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Benchmark data directory not found: {data_dir}")

    for filename in sorted(os.listdir(data_dir)):
        if filename.endswith(".json"):
            continue
        file_path = os.path.join(data_dir, filename)
        if not os.path.isfile(file_path):
            continue

        logger.info(f"Ingesting file: {filename}")
        print(f"Ingesting file: {filename}...")
        try:
            ingest_file(file_path)
        except Exception as e:
            logger.error(f"Failed to ingest file {filename}: {e}", exc_info=True)
            print(f"[WARNING] Failed to ingest file {filename}: {e}")
        # Ingestion cooldown sleep
        time.sleep(4.0)

    # 3. Load and parse test cases
    test_cases_path = os.path.join(data_dir, "test_cases.json")
    if not os.path.exists(test_cases_path):
        raise FileNotFoundError(f"Test cases file not found: {test_cases_path}")

    with open(test_cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []

    # 4. Iterate through test cases
    for case in cases:
        # Check required fields
        required_fields = ["id", "query", "expected_sources", "expected_content_types", "reference_answer"]
        missing = [f for f in required_fields if f not in case or case[f] is None]
        if missing:
            err_msg = f"Malformed test case: missing field(s) {', '.join(missing)}"
            logger.error(err_msg)
            print(f"[ERROR] {err_msg}")
            results.append({
                "id": case.get("id"),
                "query": case.get("query"),
                "error": err_msg,
                "status": "malformed",
            })
            continue

        case_id = case["id"]
        query = case["query"]
        expected_sources = case["expected_sources"]
        expected_content_types = case["expected_content_types"]
        reference_answer = case["reference_answer"]

        print(f"Executing case {case_id}...")
        try:
            # Context retrieval and generation inside trace()
            with trace() as state:
                context, image_paths = retrieve_context(state, query)
                candidate_answer = generate_answer(state, query, context, image_paths)

            # Embed the query to retrieve the matched chunks and compute precision/recall
            query_embeddings = generate_embeddings([query])
            if query_embeddings:
                query_vector = query_embeddings[0]
                retrieved_results = query_vector_store(query_vector, n_results=3)
                retrieved_metadatas = retrieved_results.get("metadatas", [[]])[0] if retrieved_results.get("metadatas") else []
                # Filter out None values
                retrieved_metadatas = [m for m in retrieved_metadatas if m is not None]
            else:
                retrieved_metadatas = []

            precision, recall = calculate_precision_recall(
                retrieved_metadatas=retrieved_metadatas,
                expected_sources=expected_sources,
                expected_content_types=expected_content_types,
            )

            # Cooldown sleep (4.0s)
            time.sleep(4.0)

            # Evaluate response quality
            quality_score = evaluate_response_quality(candidate_answer, reference_answer)

            # Cooldown sleep (4.0s)
            time.sleep(4.0)

            results.append({
                "id": case_id,
                "query": query,
                "precision": precision,
                "recall": recall,
                "quality_score": quality_score,
                "candidate_answer": candidate_answer,
                "reference_answer": reference_answer,
                "status": "success",
            })
            print(f"Case {case_id} completed successfully. Score: {quality_score}")

        except Exception as e:
            err_msg = f"Execution error: {str(e)}"
            logger.error(err_msg, exc_info=True)
            print(f"[ERROR] {err_msg} in case {case_id}")
            results.append({
                "id": case_id,
                "query": query,
                "error": err_msg,
                "status": "failed",
            })
            # Still cooldown sleep on failure to stay under limit
            time.sleep(4.0)

    # 5. Output Markdown table
    print("\n" + "=" * 80)
    print(" RAG PIPELINE BENCHMARK RESULTS")
    print("=" * 80)

    # Table headers
    headers = ["Case ID", "Query", "Precision", "Recall", "Quality Score", "Status"]
    header_str = " | ".join(headers)
    separator_str = " | ".join(["---"] * len(headers))
    print(f"| {header_str} |")
    print(f"| {separator_str} |")

    for r in results:
        status = r.get("status", "unknown")
        case_id = r.get("id") or "N/A"
        query = r.get("query") or "N/A"
        query_truncated = query if len(query) <= 40 else query[:37] + "..."

        if status == "success":
            p_val = f"{r.get('precision', 0.0):.2f}"
            r_val = f"{r.get('recall', 0.0):.2f}"
            q_val = f"{r.get('quality_score', 0.0):.2f}"
            print(f"| {case_id} | {query_truncated} | {p_val} | {r_val} | {q_val} | {status} |")
        else:
            err = r.get("error") or "Unknown error"
            print(f"| {case_id} | {query_truncated} | N/A | N/A | N/A | {status} ({err}) |")

    # 6. Save results to JSON
    results_file = "benchmark_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved benchmark results to {os.path.abspath(results_file)}")

    return results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    run_benchmark()

