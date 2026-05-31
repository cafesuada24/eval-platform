import time
from typing import Annotated

from app.core.config import settings
from app.core.documents.models import DocumentMetadata
from app.core.documents.ports import DocumentRepository
from app.core.vector_storage.models import RAGParameters, VectorDocument
from app.core.vector_storage.ports import VectorStoragePort
from fastapi import Depends


class DocumentService:
    """Application service for handling documents and their vector embeddings."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        vector_storage: VectorStoragePort,
    ):
        self._document_repo = document_repo
        self._vector_storage = vector_storage

    def save_and_index_document(self, filename: str, text_content: str, size: int) -> DocumentMetadata:
        """Save document metadata to the repository and index text into vector storage."""
        # Persist the file metadata to disk
        file_id = f'art-{int(time.time() * 1000)}'

        metadata = DocumentMetadata(
            id=file_id, name=filename, text=text_content, size=size,
        )

        self._document_repo.save(metadata)

        # Index into vector storage
        vec_doc = VectorDocument(
            id=file_id,
            text=text_content,
            metadata={"filename": filename, "size": size}
        )
        
        rag_params = RAGParameters(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            top_k=settings.rag_top_k,
        )
        
        self._vector_storage.index_document(vec_doc, rag_params)

        return metadata

    def list_documents(self) -> list[DocumentMetadata]:
        """List all documents."""
        return self._document_repo.list_all()

    def get_document(self, document_id: str) -> DocumentMetadata | None:
        """Get a document by ID."""
        return self._document_repo.find_by_id(document_id)

    def delete_document(self, document_id: str) -> None:
        """Delete document from repository and remove its chunks from vector storage."""
        self._document_repo.delete(document_id)
        self._vector_storage.delete_document(document_id)
