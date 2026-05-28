import io
import uuid
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from typing import List

# Initialize ChromaDB client (in-memory)
client = chromadb.Client(Settings(is_persistent=False))
embedding_function = embedding_functions.DefaultEmbeddingFunction()

collection = client.get_or_create_collection(
    name="documents",
    embedding_function=embedding_function
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

def process_upload(file_bytes: bytes, mime_type: str, file_name: str = "") -> None:
    """
    Process incoming files, chunk them if text/pdf, and store in ChromaDB.
    Images are handled natively by the model, so we skip vectorizing them here.
    """
    text_content = ""

    if mime_type == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content += text + "\n"
        except Exception as e:
            print(f"Error reading PDF {file_name}: {e}")
            return
            
    elif mime_type == "text/plain":
        try:
            text_content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            print(f"Error decoding text file {file_name}")
            return
            
    elif mime_type.startswith("image/"):
        # We rely on Gemini's native multimodal capabilities for images.
        # They will be passed as base64 in the generator.
        pass
        
    if text_content.strip():
        chunks = text_splitter.split_text(text_content)
        if not chunks:
            return
            
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"source": file_name, "mime_type": mime_type} for _ in chunks]
        
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

def retrieve_context(query: str, n_results: int = 3) -> List[str]:
    """
    Perform a similarity search on the vector store and return the top-K matching text chunks.
    """
    if collection.count() == 0:
        return []
        
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count())
    )
    
    documents = results.get("documents")
    if documents and len(documents) > 0:
        return documents[0]
    return []
