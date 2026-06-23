"""ChromaDB storage and querying interface module."""

import os
import uuid
from typing import Any

import chromadb

# Dynamically resolve DB_DIR to be absolute, relative to the module file.
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "db"))
chroma_client = chromadb.PersistentClient(path=DB_DIR)
collection = chroma_client.get_or_create_collection(name="ai_chat_docs")


def add_chunks_to_db(
    chunks: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict[str, Any]] | None,
    source: str,
) -> None:
    """Adds text chunks with pre-computed embeddings and metadata to ChromaDB."""
    if not chunks:
        return

    # If metadatas is not provided or is empty, initialize it
    if not metadatas:
        metadatas = [{} for _ in chunks]

    # Ensure source filename is mapped under source_file
    for meta in metadatas:
        meta.setdefault("source_file", source)

    # Validate that lengths of chunks, embeddings, and metadatas match
    if len(chunks) != len(embeddings) or len(chunks) != len(metadatas):
        raise ValueError("Length of chunks, embeddings, and metadatas must match.")

    # Generate unique string IDs for each chunk
    ids = [str(uuid.uuid4()) for _ in chunks]

    # Add to ChromaDB collection
    collection.add(
        documents=chunks,
        embeddings=embeddings,  # type: ignore[arg-type]
        metadatas=metadatas,  # type: ignore[arg-type]
        ids=ids,
    )


def query_vector_store(query_vector: list[float], n_results: int = 3) -> dict[str, Any]:
    """Queries the ChromaDB collection with a query vector, limiting n_results to collection size."""
    count = collection.count()
    if count == 0:
        return {}

    # Call query with single query vector
    return collection.query(  # type: ignore[return-value]
        query_embeddings=[query_vector],  # type: ignore[arg-type]
        n_results=min(n_results, count),
    )


def get_indexed_files() -> dict[str, list[dict[str, Any]]]:
    """Returns all indexed files grouped by source_file.

    Each value is a list of chunk records with keys: document, metadata, id.
    Chunks missing the source_file metadata key are silently skipped.
    """
    result = collection.get(include=["documents", "metadatas"])

    documents: list[str] = result.get("documents") or []
    metadatas: list[dict[str, Any]] = result.get("metadatas") or []
    ids: list[str] = result.get("ids") or []

    file_index: dict[str, list[dict[str, Any]]] = {}
    for doc, meta, doc_id in zip(documents, metadatas, ids):
        source = meta.get("source_file")
        if not source:
            continue
        file_index.setdefault(source, []).append(
            {"document": doc, "metadata": meta, "id": doc_id}
        )

    return file_index
