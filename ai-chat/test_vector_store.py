"""Tests for the ChromaDB interface module."""

import uuid
from unittest.mock import MagicMock, patch

import chromadb
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

# Now import the functions to test safely, ensuring any previously imported
# unmocked version is removed from sys.modules to prevent test pollution.
import sys

if "vector_store" in sys.modules:
    del sys.modules["vector_store"]

from vector_store import add_chunks_to_db, delete_file, get_indexed_files, query_vector_store  # noqa: E402


@pytest.fixture
def clean_collection():
    """Provides a fresh in-memory ChromaDB collection, patching the module-level one."""
    client = chromadb.EphemeralClient()
    col = client.get_or_create_collection(f"test_{uuid.uuid4().hex}")
    with patch("vector_store.collection", col):
        yield col


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


class TestGetIndexedFiles:
    """Tests for get_indexed_files()."""

    def test_returns_empty_dict_when_collection_empty(self, clean_collection):
        result = get_indexed_files()
        assert result == {}

    def test_groups_chunks_by_source_file(self, clean_collection):
        # Arrange — add 2 chunks for file_a and 1 for file_b
        clean_collection.add(
            documents=["chunk 1", "chunk 2", "chunk 3"],
            embeddings=[[0.1] * 768, [0.2] * 768, [0.3] * 768],
            metadatas=[
                {"source_file": "file_a.txt", "page_number": 1, "content_type": "text"},
                {"source_file": "file_a.txt", "page_number": 1, "content_type": "text"},
                {"source_file": "file_b.txt", "page_number": 1, "content_type": "text"},
            ],
            ids=["id1", "id2", "id3"],
        )

        result = get_indexed_files()

        assert set(result.keys()) == {"file_a.txt", "file_b.txt"}
        assert len(result["file_a.txt"]) == 2
        assert len(result["file_b.txt"]) == 1

    def test_chunk_record_has_expected_keys(self, clean_collection):
        clean_collection.add(
            documents=["hello world"],
            embeddings=[[0.1] * 768],
            metadatas=[{"source_file": "doc.txt", "page_number": 1, "content_type": "text"}],
            ids=["id-x"],
        )

        result = get_indexed_files()
        chunk = result["doc.txt"][0]

        assert "document" in chunk
        assert "metadata" in chunk
        assert "id" in chunk
        assert chunk["document"] == "hello world"
        assert chunk["metadata"]["source_file"] == "doc.txt"

    def test_skips_chunks_with_missing_source_file(self, clean_collection):
        clean_collection.add(
            documents=["orphan chunk"],
            embeddings=[[0.1] * 768],
            metadatas=[{"page_number": 1, "content_type": "text"}],  # no source_file
            ids=["orphan-id"],
        )

        result = get_indexed_files()
        assert result == {}

    def test_skips_chunks_with_empty_source_file(self, clean_collection):
        clean_collection.add(
            documents=["chunk with blank source"],
            embeddings=[[0.1] * 768],
            metadatas=[{"source_file": "", "page_number": 1, "content_type": "text"}],
            ids=["blank-id"],
        )
        result = get_indexed_files()
        assert result == {}


class TestDeleteFile:
    """Tests for delete_file()."""

    def test_deletes_all_chunks_for_source_file(self, clean_collection):
        # Arrange
        clean_collection.add(
            documents=["chunk a", "chunk b", "chunk c"],
            embeddings=[[0.1] * 768, [0.2] * 768, [0.3] * 768],
            metadatas=[
                {"source_file": "target.pdf", "page_number": 1, "content_type": "text"},
                {"source_file": "target.pdf", "page_number": 2, "content_type": "text"},
                {"source_file": "other.txt", "page_number": 1, "content_type": "text"},
            ],
            ids=["t1", "t2", "o1"],
        )

        deleted = delete_file("target.pdf")

        assert deleted == 2
        remaining = clean_collection.get(where={"source_file": "target.pdf"})
        assert len(remaining["ids"]) == 0
        # other.txt untouched
        other = clean_collection.get(where={"source_file": "other.txt"})
        assert len(other["ids"]) == 1

    def test_returns_zero_when_file_not_found(self, clean_collection):
        deleted = delete_file("nonexistent.pdf")
        assert deleted == 0

    def test_returns_correct_count_for_single_chunk_file(self, clean_collection):
        clean_collection.add(
            documents=["only chunk"],
            embeddings=[[0.1] * 768],
            metadatas=[{"source_file": "solo.txt", "page_number": 1, "content_type": "text"}],
            ids=["s1"],
        )

        deleted = delete_file("solo.txt")
        assert deleted == 1
