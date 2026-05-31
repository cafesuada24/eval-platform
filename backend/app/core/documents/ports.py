from typing import Protocol

from app.core.documents.models import DocumentMetadata


class DocumentRepository(Protocol):
    """Repository for documents."""

    def find_by_id(self, document_id: str) -> DocumentMetadata | None:
        """Find a document by ID."""
        ...

    def list_all(self) -> list[DocumentMetadata]:
        """List all documents."""
        ...

    def save(self, document: DocumentMetadata) -> None:
        """Save a document."""
        ...

    def delete(self, document_id: str) -> None:
        """Delete a document."""
        ...
