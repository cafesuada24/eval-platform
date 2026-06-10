"""Tests for the ChromaDB interface module."""

from unittest.mock import MagicMock, patch

import pytest

# Test constants to avoid PLR2004 (magic value comparison)
EXPECTED_CHUNKS_COUNT = 2

# We mock chromadb.PersistentClient at the module level before importing vector_store.
# This prevents the module-level initialization in vector_store.py from hitting
# the real database, avoiding issues with conflicting embedding dimensions.
mock_collection = MagicMock()
mock_client = MagicMock()
mock_client.get_or_create_collection.return_value = mock_collection

persistent_client_patcher = patch("chromadb.PersistentClient", return_value=mock_client)
persistent_client_patcher.start()

# Now import the functions to test safely
from vector_store import add_chunks_to_db, query_vector_store  # noqa: E402


@pytest.fixture(autouse=True)
def reset_mocks() -> None:
    """Reset the mock collection and client call states before each test."""
    mock_collection.reset_mock()
    mock_client.reset_mock()


def test_add_chunks_to_db_success() -> None:
    """Test successful addition of chunks with embeddings and metadata."""
    chunks = ["chunk1", "chunk2"]
    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    metadatas = [{"key": "val1"}, {}]
    source = "doc.txt"

    add_chunks_to_db(chunks, embeddings, metadatas, source)

    # Verify collection.add was called
    assert mock_collection.add.called
    kwargs = mock_collection.add.call_args[1]

    # Verify documents and embeddings passed correctly
    assert kwargs["documents"] == chunks
    assert kwargs["embeddings"] == embeddings

    # Verify source was added to metadata using source_file
    expected_metadatas = [
        {"key": "val1", "source_file": "doc.txt"},
        {"source_file": "doc.txt"},
    ]
    assert kwargs["metadatas"] == expected_metadatas

    # Verify unique IDs were generated
    ids = kwargs["ids"]
    assert len(ids) == EXPECTED_CHUNKS_COUNT
    assert ids[0] != ids[1]
    assert isinstance(ids[0], str)
    assert isinstance(ids[1], str)


def test_add_chunks_to_db_empty() -> None:
    """Test that empty chunks list returns early without adding."""
    add_chunks_to_db([], [], [], "doc.txt")
    mock_collection.add.assert_not_called()


def test_add_chunks_to_db_none_metadata() -> None:
    """Test that None/empty metadatas argument is initialized correctly."""
    chunks = ["chunk1"]
    embeddings = [[0.1, 0.2]]
    source = "doc.txt"

    # Testing with None metadatas passed
    add_chunks_to_db(chunks, embeddings, None, source)

    # Verify collection.add was called with generated metadatas containing source_file
    assert mock_collection.add.called
    kwargs = mock_collection.add.call_args[1]
    assert kwargs["metadatas"] == [{"source_file": "doc.txt"}]


def test_query_vector_store_success() -> None:
    """Test query operation when collection has data."""
    # Mock count to be greater than 0
    mock_collection.count.return_value = 5
    mock_collection.query.return_value = {"ids": [["id1"]], "documents": [["chunk1"]]}

    query_vector = [0.1, 0.2]
    res = query_vector_store(query_vector, n_results=3)

    assert res == {"ids": [["id1"]], "documents": [["chunk1"]]}
    mock_collection.query.assert_called_once_with(
        query_embeddings=[query_vector],
        n_results=3,
    )


def test_query_vector_store_empty_collection() -> None:
    """Test query operation when collection count is 0."""
    mock_collection.count.return_value = 0

    query_vector = [0.1, 0.2]
    res = query_vector_store(query_vector, n_results=3)

    assert res == {}
    mock_collection.query.assert_not_called()


def test_query_vector_store_n_results_cap() -> None:
    """Test query operation limits n_results to collection size."""
    # Collection count is 2, requested n_results is 5
    mock_collection.count.return_value = 2
    mock_collection.query.return_value = {"ids": [["id1", "id2"]]}

    query_vector = [0.1, 0.2]
    res = query_vector_store(query_vector, n_results=5)

    assert res == {"ids": [["id1", "id2"]]}
    mock_collection.query.assert_called_once_with(
        query_embeddings=[query_vector],
        n_results=2,
    )
