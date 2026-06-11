"""Tests for the RAG engine module."""

from unittest.mock import MagicMock, patch

import pytest

# We must import RuntimeState for typing/spec verification
from evalplatform_sdk.models import RuntimeState
from PIL import Image

# Import functions under test
from rag_engine import generate_answer, retrieve_context

# Constants to avoid magic values
QUERY_VECTOR = [0.1, 0.2, 0.3]
RETRIEVED_TEXT_1 = "Document chunk 1 content"
RETRIEVED_TEXT_2 = "Document chunk 2 content"
IMAGE_PATH_VAL = "/home/serein/SourceCodes/eval-platform/ai-chat/sample.png"


def test_retrieve_context_success() -> None:
    """Verify retrieve_context behaves correctly under successful conditions."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_rt = MagicMock()
    mock_state.track_retrieval.return_value.__enter__.return_value = mock_rt

    query = "test query"
    n_results = 2

    # Mock embeddings
    mock_embeddings = [QUERY_VECTOR]

    # Mock query results
    mock_query_results = {
        "documents": [[RETRIEVED_TEXT_1, RETRIEVED_TEXT_2]],
        "metadatas": [[
            {"source_file": "doc1.txt", "content_type": "text"},
            {"source_file": "doc2.txt", "content_type": "image_caption", "asset_path": IMAGE_PATH_VAL},
        ]],
        "distances": [[0.1, 0.2]],
    }

    with patch("rag_engine.generate_embeddings", return_value=mock_embeddings) as mock_embed, \
         patch("rag_engine.query_vector_store", return_value=mock_query_results) as mock_query:

        context, image_paths = retrieve_context(mock_state, query, n_results=n_results)

        # Assert correct embedding generation & query calls
        mock_embed.assert_called_once_with([query])
        mock_query.assert_called_once_with(QUERY_VECTOR, n_results)

        # Assert telemetry calls
        mock_state.track_retrieval.assert_called_once()
        mock_rt.query.assert_called_once_with(query)
        assert mock_rt.add_chunk.call_count == 2
        mock_rt.add_chunk.assert_any_call(
            document="doc1.txt",
            content=RETRIEVED_TEXT_1,
            confidence=0.1,
        )
        mock_rt.add_chunk.assert_any_call(
            document="doc2.txt",
            content=RETRIEVED_TEXT_2,
            confidence=0.2,
        )

        # Assert returned context and images
        assert context == f"{RETRIEVED_TEXT_1}\n\n{RETRIEVED_TEXT_2}"
        assert image_paths == [IMAGE_PATH_VAL]


def test_retrieve_context_no_embeddings() -> None:
    """Verify retrieve_context returns empty context and empty image list when embeddings fail."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_rt = MagicMock()
    mock_state.track_retrieval.return_value.__enter__.return_value = mock_rt

    with patch("rag_engine.generate_embeddings", return_value=[]) as mock_embed:
        context, image_paths = retrieve_context(mock_state, "empty query")
        assert context == ""
        assert image_paths == []
        mock_embed.assert_called_once_with(["empty query"])


@patch("rag_engine.Image.open")
@patch("rag_engine.genai.Client")
def test_generate_answer_success(mock_client_class: MagicMock, mock_image_open: MagicMock) -> None:
    """Verify generate_answer processes inputs, formats prompt, calls Gemini, and logs telemetry."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Mock response
    mock_response = MagicMock()
    mock_response.text = "Generated answer text"
    mock_response.usage_metadata.prompt_token_count = 120
    mock_response.usage_metadata.candidates_token_count = 35
    mock_client.models.generate_content.return_value = mock_response

    # Mock PIL images
    mock_img = MagicMock(spec=Image.Image)
    mock_image_open.return_value = mock_img

    query = "Find the total amount."
    context = "Context info."
    image_paths = ["/path/to/img.png"]

    answer = generate_answer(mock_state, query, context, image_paths)

    assert answer == "Generated answer text"

    # Verify PIL image opened
    mock_image_open.assert_called_once_with("/path/to/img.png")

    # Verify Client called with model and correct contents structure
    mock_client.models.generate_content.assert_called_once()
    call_kwargs = mock_client.models.generate_content.call_args[1]
    assert call_kwargs["model"] == "gemini-3.1-flash-lite"
    assert len(call_kwargs["contents"]) == 2
    assert call_kwargs["contents"][0] == mock_img
    assert "Context info." in call_kwargs["contents"][1]
    assert "Find the total amount." in call_kwargs["contents"][1]

    # Verify telemetry tracker calls
    mock_gen_tracker.model_info.assert_called_once_with(provider="google", model_name="gemini-3.1-flash-lite")
    mock_gen_tracker.user_input.assert_called_once_with(query)
    mock_gen_tracker.token_usage.assert_called_once_with(input_tokens=120, output_tokens=35)
    mock_gen_tracker.output_text.assert_called_once_with("Generated answer text")


@patch("rag_engine.time.sleep")
@patch("rag_engine.Image.open")
@patch("rag_engine.genai.Client")
def test_generate_answer_retries_and_succeeds(
    mock_client_class: MagicMock,
    mock_image_open: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    """Verify generate_answer performs exponential backoff and succeeds on a retry."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "Answer on retry"
    mock_response.usage_metadata = None  # Telemetry should skip token logging if missing

    # Fail twice, then succeed
    mock_client.models.generate_content.side_effect = [
        Exception("API Error 1"),
        Exception("API Error 2"),
        mock_response,
    ]

    answer = generate_answer(mock_state, "query", "context", [])

    assert answer == "Answer on retry"
    assert mock_client.models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2
    # Sleep delays: 1s, then 2s
    mock_sleep.assert_any_call(1.0)
    mock_sleep.assert_any_call(2.0)
    mock_gen_tracker.token_usage.assert_not_called()


@patch("rag_engine.time.sleep")
@patch("rag_engine.Image.open")
@patch("rag_engine.genai.Client")
def test_generate_answer_retries_failure(
    mock_client_class: MagicMock,
    mock_image_open: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    """Verify generate_answer fails and propagates exception after maximum retries."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Fails all 4 times (1 initial + 3 retries)
    mock_client.models.generate_content.side_effect = [
        Exception("Error 1"),
        Exception("Error 2"),
        Exception("Error 3"),
        Exception("Error 4"),
    ]

    with pytest.raises(Exception, match="Error 4"):
        generate_answer(mock_state, "query", "context", [])

    assert mock_client.models.generate_content.call_count == 4
    assert mock_sleep.call_count == 3
    sleep_args = [arg[0][0] for arg in mock_sleep.call_args_list]
    assert sleep_args == [1.0, 2.0, 4.0]
