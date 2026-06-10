from pypdf import PdfReader

def extract_text_from_txt(file_path: str) -> str:
    """Reads and returns the contents of a text file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def extract_text_from_pdf_fallback(file_path: str) -> tuple[str, list[dict]]:
    """Fallback parser extracting text page-by-page using pypdf."""
    pdf_reader = PdfReader(file_path)
    unified_markdown_parts = []
    for page_idx, page in enumerate(pdf_reader.pages):
        page_num = page_idx + 1
        page_text = page.extract_text() or ""
        page_marker = f"\n\n<!-- PAGE_{page_num} -->\n\n"
        unified_markdown_parts.append(page_marker + page_text)
    return "".join(unified_markdown_parts), []
