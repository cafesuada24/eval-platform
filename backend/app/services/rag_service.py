import os
from io import BytesIO
import chromadb
import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.engine.orchestrator import FIXTURES_DIR

if os.environ.get("PYTEST_CURRENT_TEST"):
    # Use isolated in-memory ephemeral client for fast, self-contained tests
    chroma_client = chromadb.EphemeralClient()
    from chromadb.api.types import Documents, Embeddings, EmbeddingFunction

    class MockEmbeddingFunction(EmbeddingFunction):
        def __call__(self, input: Documents) -> Embeddings:
            return [[0.0] * 384 for _ in input]

        def name(self) -> str:
            return "mock"

    collection = chroma_client.get_or_create_collection(
        name="uploaded_documents_test",
        embedding_function=MockEmbeddingFunction()
    )
else:
    CHROMADB_DIR = os.path.join(FIXTURES_DIR, 'chromadb')
    os.makedirs(CHROMADB_DIR, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMADB_DIR)
    collection = chroma_client.get_or_create_collection(name="uploaded_documents")


def extract_text_from_pdf_local(pdf_bytes: bytes) -> str:
    """Extract raw text from a PDF file using pypdf locally."""
    try:
        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"pypdf extraction failed: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks using RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)


def index_document(file_id: str, filename: str, text: str) -> None:
    """Split document text and ingest chunks into ChromaDB."""
    if not text.strip():
        return

    chunks = chunk_text(text)
    if not chunks:
        return

    documents = []
    ids = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        documents.append(chunk)
        ids.append(f"{file_id}-chunk-{i}")
        metadatas.append({
            "file_id": file_id,
            "file_name": filename,
            "chunk_index": i
        })

    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )


def delete_document_from_index(file_id: str) -> None:
    """Delete all chunks belonging to a file_id from ChromaDB."""
    try:
        collection.delete(where={"file_id": file_id})
    except Exception as e:
        print(f"Failed to delete document {file_id} from ChromaDB: {e}")


def get_indexed_chunks_count() -> int:
    """Return the total number of chunks indexed in the collection."""
    try:
        return collection.count()
    except Exception:
        return 0


def query_vector_db(query: str, top_k: int = 2) -> str:
    """Retrieve semantically relevant chunks from ChromaDB for a given query."""
    if not query.strip():
        return ""

    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        if results and results.get("documents") and results["documents"][0]:
            matched_chunks = results["documents"][0]
            return "\n\n".join(matched_chunks)
    except Exception as e:
        print(f"ChromaDB query failed: {e}")

    return ""
