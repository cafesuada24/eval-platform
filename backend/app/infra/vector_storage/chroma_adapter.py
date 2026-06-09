import logging
from pathlib import Path

import chromadb
from app.core.vector_storage.models import QueryResult, RAGParameters, VectorDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter


class ChromaVectorStorage:
    """ChromaDB implementation of VectorStoragePort."""

    def __init__(self, persist_directory: Path, collection_name: str = 'documents'):
        """Initialize ChromaDB client and collection."""
        self.persist_directory = persist_directory
        # Ensure the directory exists
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(self.persist_directory))

        # We use the default embedding function (all-MiniLM-L6-v2)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        logging.info(f'Initialized ChromaDB vector storage at {self.persist_directory}')

    def index_document(self, document: VectorDocument, params: RAGParameters) -> None:
        """Chunk and index a document into the vector storage."""
        if not document.text.strip():
            logging.warning(f'Document {document.id} has no text to index.')
            return

        # 1. Chunk the text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=params.chunk_size,
            chunk_overlap=params.chunk_overlap,
        )
        chunks = text_splitter.split_text(document.text)

        if not chunks:
            return

        # 2. Prepare data for ChromaDB
        ids = [f'{document.id}_chunk_{i}' for i in range(len(chunks))]
        metadatas = []
        for i in range(len(chunks)):
            # Combine document metadata with chunk specific metadata
            chunk_meta = document.metadata.copy()
            chunk_meta['document_id'] = document.id
            chunk_meta['chunk_index'] = i
            metadatas.append(chunk_meta)

        # 3. Add to collection
        self.collection.add(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )
        logging.info(f'Indexed {len(chunks)} chunks for document {document.id}')

    def query(self, query_text: str, params: RAGParameters) -> list[QueryResult]:
        """Query the vector storage."""
        if not query_text.strip():
            return []

        results = self.collection.query(
            query_texts=[query_text],
            n_results=params.top_k,
        )

        query_results: list[QueryResult] = []
        if not results['documents'] or not results['documents'][0]:
            return query_results

        documents = results['documents'][0]
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []

        for i in range(len(documents)):
            text = documents[i]
            meta = metadatas[i] if i < len(metadatas) else {}
            # distances in ChromaDB (with L2 squared by default) lower is better
            score = distances[i] if i < len(distances) else 0.0
            doc_id = str(meta.get('document_id', f'unknown_{i}'))

            vec_doc = VectorDocument(id=doc_id, text=text, metadata=meta)
            query_results.append(QueryResult(document=vec_doc, score=score))

        return sorted(query_results, key=lambda x: -x.score)

    def delete_document(self, document_id: str) -> None:
        """Delete a document and all its chunks from the vector storage."""
        self.collection.delete(
            where={'document_id': document_id},
        )
        logging.info(f'Deleted chunks for document {document_id}')
