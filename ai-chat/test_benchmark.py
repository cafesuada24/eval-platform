"""Tests for benchmark metrics helper functions."""

import logging
import pytest
from benchmark import calculate_precision_recall, parse_semantic_score, retry_api_call


def test_calculate_precision_recall_happy_path() -> None:
    """Verify precision and recall are computed correctly for normal inputs."""
    retrieved = [
        {"source_file": "doc1.txt", "content_type": "text"},          # Relevant
        {"source_file": "doc1.txt", "content_type": "image_caption"}, # Relevant
        {"source_file": "doc2.txt", "content_type": "text"},          # Irrelevant (wrong source)
        {"source_file": "doc1.txt", "content_type": "other"},         # Irrelevant (wrong type)
    ]
    expected_sources = ["doc1.txt"]
    expected_content_types = ["text", "image_caption"]

    precision, recall = calculate_precision_recall(
        retrieved_metadatas=retrieved,
        expected_sources=expected_sources,
        expected_content_types=expected_content_types,
    )

    # 2 out of 4 retrieved chunks are relevant -> precision = 0.5
    # 2 relevant retrieved chunks out of (1 * 2 = 2) expected target space -> recall = 2 / 2 = 1.0
    assert precision == pytest.approx(0.5)
    assert recall == pytest.approx(1.0)


def test_calculate_precision_recall_empty_retrieved() -> None:
    """Verify precision and recall return 0.0 if retrieved list is empty."""
    precision, recall = calculate_precision_recall(
        retrieved_metadatas=[],
        expected_sources=["doc1.txt"],
        expected_content_types=["text"],
    )
    assert precision == 0.0
    assert recall == 0.0


def test_calculate_precision_recall_empty_expected() -> None:
    """Verify recall is 0.0 if expected list is empty (denominator is 0)."""
    retrieved = [{"source_file": "doc1.txt", "content_type": "text"}]
    
    # Empty sources
    precision, recall = calculate_precision_recall(
        retrieved_metadatas=retrieved,
        expected_sources=[],
        expected_content_types=["text"],
    )
    assert precision == 0.0
    assert recall == 0.0

    # Empty content types
    precision, recall = calculate_precision_recall(
        retrieved_metadatas=retrieved,
        expected_sources=["doc1.txt"],
        expected_content_types=[],
    )
    assert precision == 0.0
    assert recall == 0.0


def test_calculate_precision_recall_cap_recall() -> None:
    """Verify recall is capped at 1.0 when relevant chunks retrieved exceeds Cartesian product size."""
    retrieved = [
        {"source_file": "doc1.txt", "content_type": "text"},
        {"source_file": "doc1.txt", "content_type": "text"},
        {"source_file": "doc1.txt", "content_type": "text"},
    ]
    expected_sources = ["doc1.txt"]
    expected_content_types = ["text"]

    precision, recall = calculate_precision_recall(
        retrieved_metadatas=retrieved,
        expected_sources=expected_sources,
        expected_content_types=expected_content_types,
    )
    # All 3 chunks are relevant -> precision = 1.0
    # Denominator is 1 * 1 = 1. Relevant retrieved count is 3.
    # Raw recall would be 3.0, but capped at 1.0.
    assert precision == pytest.approx(1.0)
    assert recall == pytest.approx(1.0)


def test_parse_semantic_score_happy_path() -> None:
    """Verify parse_semantic_score extracts the first matching float/int from a string."""
    assert parse_semantic_score("0.85") == pytest.approx(0.85)
    assert parse_semantic_score("The score is 0.95 and is great.") == pytest.approx(0.95)
    assert parse_semantic_score("Score: 1") == pytest.approx(1.0)
    assert parse_semantic_score("Semantic score: 0.12345") == pytest.approx(0.12345)


def test_parse_semantic_score_boundaries() -> None:
    """Verify parse_semantic_score caps the score between 0.0 and 1.0."""
    assert parse_semantic_score("1.5") == pytest.approx(1.0)
    assert parse_semantic_score("-0.5") == pytest.approx(0.5)
    assert parse_semantic_score("99.9") == pytest.approx(1.0)


def test_parse_semantic_score_not_found_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Verify a warning is logged and 0.0 returned when no score is found."""
    with caplog.at_level(logging.WARNING):
        score = parse_semantic_score("No score here at all!")
        assert score == 0.0
        assert len(caplog.records) == 1
        assert "warning" in caplog.text.lower() or "no" in caplog.text.lower()


def test_retry_api_call_succeeds() -> None:
    """Verify retry_api_call succeeds after a failure and sleeps once."""
    from unittest.mock import patch

    calls = []
    def mock_func():
        calls.append(1)
        if len(calls) == 1:
            raise ValueError("First call fails")
        return "success"

    with patch("time.sleep") as mock_sleep:
        result = retry_api_call(mock_func)
        assert result == "success"
        assert len(calls) == 2
        mock_sleep.assert_called_once_with(2.0)


def test_retry_api_call_aborts_after_retries() -> None:
    """Verify retry_api_call propagates exception after max retries with exponential backoff."""
    from unittest.mock import MagicMock, patch

    mock_func = MagicMock(side_effect=ValueError("Persistent error"))

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(ValueError, match="Persistent error"):
            retry_api_call(mock_func)

        assert mock_func.call_count == 6  # 1 initial + 5 retries
        assert mock_sleep.call_count == 5
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert delays == [2.0, 4.0, 8.0, 16.0, 32.0]


def test_clear_database() -> None:
    """Verify clear_database deletes items only if count > 0."""
    from unittest.mock import patch
    with patch("benchmark.collection") as mock_collection:
        # Case 1: Count is 0 -> should not call delete
        mock_collection.count.return_value = 0
        from benchmark import clear_database
        clear_database()
        mock_collection.delete.assert_not_called()

        # Case 2: Count is > 0 -> should call delete
        mock_collection.count.return_value = 5
        clear_database()
        mock_collection.delete.assert_called_once_with(where={})


def test_evaluate_response_quality() -> None:
    """Verify evaluate_response_quality calls Gemini and parses the score."""
    from unittest.mock import MagicMock, patch
    with patch("benchmark.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "0.85"
        mock_client.models.generate_content.return_value = mock_response

        from benchmark import evaluate_response_quality
        score = evaluate_response_quality("candidate", "reference")
        assert score == pytest.approx(0.85)
