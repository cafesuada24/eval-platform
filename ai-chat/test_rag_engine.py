"""Tests for the RAG engine module."""

from unittest.mock import MagicMock, patch

import pytest

# We must import RuntimeState for typing/spec verification
from evalplatform_sdk.models import RuntimeState

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


# ── Forced-retrieval path ────────────────────────────────────────────────────

@patch("rag_engine.retrieve_context")
@patch("rag_engine.genai.Client")
def test_generate_answer_forced_retrieval(
    mock_client_class: MagicMock, mock_retrieve: MagicMock
) -> None:
    """force_retrieve=True: always calls retrieve_context and returns model answer."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_retrieve.return_value = ("some context text", [])

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "Forced answer"
    mock_response.usage_metadata = None
    mock_client.models.generate_content.return_value = mock_response

    answer = generate_answer(mock_state, "What is X?", force_retrieve=True)

    assert answer == "Forced answer"
    mock_retrieve.assert_called_once_with(mock_state, "What is X?")
    mock_client.models.generate_content.assert_called_once()
    # Verify context injected into prompt
    call_contents = mock_client.models.generate_content.call_args[1]["contents"]
    prompt = call_contents[-1]
    assert "some context text" in prompt
    assert "What is X?" in prompt


@patch("rag_engine.retrieve_context")
@patch("rag_engine.genai.Client")
def test_generate_answer_forced_retrieval_logs_tokens(
    mock_client_class: MagicMock, mock_retrieve: MagicMock
) -> None:
    """force_retrieve=True: records token usage when usage_metadata is present."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_retrieve.return_value = ("ctx", [])

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "Answer"
    mock_response.usage_metadata.prompt_token_count = 50
    mock_response.usage_metadata.candidates_token_count = 20
    mock_client.models.generate_content.return_value = mock_response

    generate_answer(mock_state, "query", force_retrieve=True)

    mock_gen_tracker.token_usage.assert_called_once_with(input_tokens=50, output_tokens=20)


@patch("rag_engine.time.sleep")
@patch("rag_engine.retrieve_context")
@patch("rag_engine.genai.Client")
def test_generate_answer_forced_retries_and_succeeds(
    mock_client_class: MagicMock,
    mock_retrieve: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    """force_retrieve=True: retries with exponential backoff on transient errors."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_retrieve.return_value = ("ctx", [])

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "Answer on retry"
    mock_response.usage_metadata = None

    mock_client.models.generate_content.side_effect = [
        Exception("API Error 1"),
        Exception("API Error 2"),
        mock_response,
    ]

    answer = generate_answer(mock_state, "query", force_retrieve=True)

    assert answer == "Answer on retry"
    assert mock_client.models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1.0)
    mock_sleep.assert_any_call(2.0)


@patch("rag_engine.time.sleep")
@patch("rag_engine.retrieve_context")
@patch("rag_engine.genai.Client")
def test_generate_answer_forced_retries_exhausted(
    mock_client_class: MagicMock,
    mock_retrieve: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    """force_retrieve=True: propagates exception after max retries."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_retrieve.return_value = ("ctx", [])

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.side_effect = [
        Exception("E1"), Exception("E2"), Exception("E3"), Exception("E4"),
    ]

    with pytest.raises(Exception, match="E4"):
        generate_answer(mock_state, "query", force_retrieve=True)

    assert mock_client.models.generate_content.call_count == 4
    sleep_args = [c[0][0] for c in mock_sleep.call_args_list]
    assert sleep_args == [1.0, 2.0, 4.0]


# ── Agentic path ─────────────────────────────────────────────────────────────

def _make_direct_response(text: str) -> MagicMock:
    """Helper: mock response where model answers directly (no function call)."""
    response = MagicMock()
    response.text = text
    response.usage_metadata = None
    # No function_call on any part
    part = MagicMock()
    part.function_call = None
    response.candidates = [MagicMock()]
    response.candidates[0].content.parts = [part]
    return response


def _make_tool_call_response(query_arg: str) -> MagicMock:
    """Helper: mock response where model calls retrieve_documents."""
    response = MagicMock()
    response.text = None
    response.usage_metadata = None
    fc = MagicMock()
    fc.args = {"query": query_arg}
    fc.name = "retrieve_documents"
    fc.id = "call_123"
    part = MagicMock()
    part.function_call = fc
    response.candidates = [MagicMock()]
    response.candidates[0].content.parts = [part]
    return response


@patch("rag_engine.retrieve_context")
@patch("rag_engine.genai.Client")
def test_generate_answer_agentic_no_retrieval(
    mock_client_class: MagicMock, mock_retrieve: MagicMock
) -> None:
    """Agentic path: model answers directly without calling the tool."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.return_value = _make_direct_response("Hi there!")

    answer = generate_answer(mock_state, "Hi!")

    assert answer == "Hi there!"
    mock_retrieve.assert_not_called()
    mock_client.models.generate_content.assert_called_once()


@patch("rag_engine.retrieve_context")
@patch("rag_engine.genai.Client")
def test_generate_answer_agentic_triggers_retrieval(
    mock_client_class: MagicMock, mock_retrieve: MagicMock
) -> None:
    """Agentic path: model calls retrieve_documents; second LLM call returns final answer."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_retrieve.return_value = ("retrieved context", [])

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    tool_call_resp = _make_tool_call_response("Paul Graham essays")
    final_resp = MagicMock()
    final_resp.text = "Final grounded answer"
    final_resp.usage_metadata = None

    mock_client.models.generate_content.side_effect = [tool_call_resp, final_resp]

    answer = generate_answer(mock_state, "What did Paul Graham write about?")

    assert answer == "Final grounded answer"
    mock_retrieve.assert_called_once_with(mock_state, "Paul Graham essays")
    assert mock_client.models.generate_content.call_count == 2

    # Assert payload of the second LLM call
    call_args_list = mock_client.models.generate_content.call_args_list
    second_call_kwargs = call_args_list[1][1]
    second_call_contents = second_call_kwargs["contents"]

    # Structure should contain:
    # 1. User original query
    # 2. Model's tool call response
    # 3. User's tool response with context
    assert len(second_call_contents) == 3
    assert second_call_contents[0].parts[0].text == "What did Paul Graham write about?"
    # The second turn content is the tool call from model
    assert second_call_contents[1] == tool_call_resp.candidates[0].content
    # The third turn contains the tool response part
    tool_resp_part = second_call_contents[2].parts[0]
    assert tool_resp_part.function_response.name == "retrieve_documents"
    assert tool_resp_part.function_response.response == {"context": "retrieved context"}
    assert tool_resp_part.function_response.id == "call_123"


@patch("rag_engine.retrieve_context")
@patch("rag_engine.genai.Client")
def test_generate_answer_agentic_bad_tool_args_falls_back(
    mock_client_class: MagicMock, mock_retrieve: MagicMock
) -> None:
    """Agentic path: malformed tool call (missing query) falls back to original query."""
    mock_state = MagicMock(spec=RuntimeState)
    mock_gen_tracker = MagicMock()
    mock_state.track_generation.return_value.__enter__.return_value = mock_gen_tracker

    mock_retrieve.return_value = ("ctx", [])

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Tool call with no 'query' key
    bad_tool_resp = MagicMock()
    bad_tool_resp.text = None
    bad_tool_resp.usage_metadata = None
    fc = MagicMock()
    fc.args = {}  # missing 'query'
    fc.name = "retrieve_documents"
    fc.id = "call_456"
    part = MagicMock()
    part.function_call = fc
    bad_tool_resp.candidates = [MagicMock()]
    bad_tool_resp.candidates[0].content.parts = [part]

    final_resp = MagicMock()
    final_resp.text = "Fallback answer"
    final_resp.usage_metadata = None

    mock_client.models.generate_content.side_effect = [bad_tool_resp, final_resp]

    answer = generate_answer(mock_state, "original query")

    assert answer == "Fallback answer"
    # retrieve_context called with original query as fallback
    mock_retrieve.assert_called_once_with(mock_state, "original query")
