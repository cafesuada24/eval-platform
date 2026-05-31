from typing import Protocol

from app.core.vector_storage.models import QueryResult, RAGParameters, VectorDocument


class VectorStoragePort(Protocol):
    """Port for interacting with a vector database."""

    def index_document(self, document: VectorDocument, params: RAGParameters) -> None:
        """Chunk and index a document into the vector storage."""
        ...

    def query(self, query_text: str, params: RAGParameters) -> list[QueryResult]:
        """Query the vector storage."""
        ...

    def delete_document(self, document_id: str) -> None:
        """Delete a document and all its chunks from the vector storage."""
        ...
