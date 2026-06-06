import os
import easyocr
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Initialize easyocr reader once
reader = easyocr.Reader(['en'])

def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def extract_text_from_image(file_path: str) -> str:
    result = reader.readtext(file_path, detail=0)
    return " ".join(result)

def extract_text_from_pdf(file_path: str) -> str:
    pdf_reader = PdfReader(file_path)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def ingest_file(file_path: str) -> list[str]:
    """Extracts text from a file and splits it into chunks."""
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".txt":
        text = extract_text_from_txt(file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        text = extract_text_from_image(file_path)
    elif ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(text)
    return chunks
