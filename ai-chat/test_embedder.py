"""Tests for the embedder module."""

from unittest.mock import MagicMock, patch

import pytest
from embedder import generate_embeddings

# Test constants to avoid PLR2004 (magic value comparison)
SINGLE_VALS: list[float] = [0.1, 0.2, 0.3]
BATCH_VALS_1: list[float] = [0.1, 0.2, 0.3]
BATCH_VALS_2: list[float] = [0.4, 0.5, 0.6]
EXPECTED_CALLS_3: int = 3
EXPECTED_CALLS_4: int = 4
EXPECTED_SLEEPS_2: int = 2
EXPECTED_SLEEPS_3: int = 3


@patch('embedder.genai.Client')
def test_generate_embeddings_single(mock_client_class: MagicMock) -> None:
    """Test generating embeddings for a single text chunk."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_embedding = MagicMock()
    mock_embedding.values = SINGLE_VALS

    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]
    mock_client.models.embed_content.return_value = mock_response

    res = generate_embeddings(['hello'])
    assert res == [SINGLE_VALS]
    mock_client.models.embed_content.assert_called_once_with(
        model='gemini-embedding-2',
        contents=['hello'],
    )


@patch('embedder.genai.Client')
def test_generate_embeddings_batch(mock_client_class: MagicMock) -> None:
    """Test generating embeddings for a batch of text chunks."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_emb1 = MagicMock()
    mock_emb1.values = BATCH_VALS_1
    mock_emb2 = MagicMock()
    mock_emb2.values = BATCH_VALS_2

    mock_response = MagicMock()
    mock_response.embeddings = [mock_emb1, mock_emb2]
    mock_client.models.embed_content.return_value = mock_response

    res = generate_embeddings(['hello', 'world'])
    assert res == [BATCH_VALS_1, BATCH_VALS_2]
    mock_client.models.embed_content.assert_called_once_with(
        model='gemini-embedding-2',
        contents=['hello', 'world'],
    )


def test_generate_embeddings_empty() -> None:
    """Test that empty inputs immediately return an empty list."""
    assert generate_embeddings([]) == []


@patch('embedder.time.sleep')
@patch('embedder.genai.Client')
def test_generate_embeddings_retry_success(
    mock_client_class: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    """Test retry behavior under rate limits/transient errors with eventual success."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_embedding = MagicMock()
    mock_embedding.values = SINGLE_VALS
    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]

    # Fails twice, then succeeds on 3rd attempt (2nd retry)
    mock_client.models.embed_content.side_effect = [
        Exception('Rate limit 429'),
        Exception('Transient 503'),
        mock_response,
    ]

    res = generate_embeddings(['hello'])
    assert res == [SINGLE_VALS]
    assert mock_client.models.embed_content.call_count == EXPECTED_CALLS_3

    # Assert sleep was called twice with correct delays (1s, then 2s)
    assert mock_sleep.call_count == EXPECTED_SLEEPS_2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


@patch('embedder.time.sleep')
@patch('embedder.genai.Client')
def test_generate_embeddings_retry_failure(
    mock_client_class: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    """Test that after max retries fail, the exception is propagated."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Fails all 4 attempts (initial + 3 retries)
    mock_client.models.embed_content.side_effect = [
        Exception('Failure 1'),
        Exception('Failure 2'),
        Exception('Failure 3'),
        Exception('Failure 4'),
    ]

    with pytest.raises(Exception, match='Failure 4'):
        generate_embeddings(['hello'])

    assert mock_client.models.embed_content.call_count == EXPECTED_CALLS_4

    # Sleep should be called 3 times: 1s, 2s, 4s
    assert mock_sleep.call_count == EXPECTED_SLEEPS_3
    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
    assert sleep_calls == [1, 2, 4]
