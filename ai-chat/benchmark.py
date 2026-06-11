"""Benchmark helper functions for multi-modal RAG metrics."""

import logging
import re
import time
from typing import Callable, TypeVar

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

