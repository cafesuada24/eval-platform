# Spec: Hybrid OCR and Captioning Pipeline Upgrade

- **Date:** 2026-06-11
- **Status:** Draft
- **Target Component:** `ai-chat` Ingestion Pipeline

---

## 1. Overview
The current RAG pipeline in `ai-chat` processes text-based PDFs and captions standard image files. However, it lacks support for WebP images, scanned PDFs (PDFs consisting of page-sized scanned images), and hybrid documents (documents with mixed digital text and scanned pages). 

This specification describes a page-by-page hybrid ingestion pipeline that:
1. Dynamically detects if a PDF page is scanned or text-based.
2. Extracts digital text locally when available.
3. Renders scanned pages to images in memory and runs OCR + captioning via the Gemini API.
4. Adds full WebP image support across the Streamlit UI and ingestion backend.

---

## 2. Design & Architecture

### Page-by-Page Ingestion Flow
For PDF ingestion, the pipeline will reuse `pymupdf4llm` to extract raw text and image files, then evaluate each page chunk:
1. Strip any markdown image references (e.g. `![](...)`) and comments from the page chunk text.
2. If the remaining text length is `< 100` characters, classify the page as **scanned**.
3. For scanned pages, open the PDF using PyMuPDF (`fitz`), load the target page, render it to a PNG image in memory (`page.get_pixmap(dpi=150)`), and send it to Gemini.
4. For text-based pages, keep the extracted text and process any embedded images using the standard captioning logic.

### Standalone and Embedded Image Ingestion
We will add `.webp` support. Standalone images and embedded PDF images will be processed using Gemini to extract both raw text and generate visual captions.

---

## 3. Component Specifications

### 3.1. `ai-chat/parser.py`
- Define a Pydantic model for structured Gemini responses:
  ```python
  from pydantic import BaseModel, Field

  class ExtractionResult(BaseModel):
      extracted_text: str = Field(
          description="The exact raw text extracted from the document page/image. Preserve structure."
      )
      visual_caption: str = Field(
          description="A detailed caption/description of any charts, diagrams, or visual elements. Leave empty if none."
      )
  ```
- Implement `extract_and_caption_bytes(image_bytes: bytes, mime_type: str) -> ExtractionResult` utilizing the Google GenAI SDK:
  - Model: `gemini-3.1-flash-lite`
  - Config: `response_mime_type="application/json"` and `response_schema=ExtractionResult`
- Update `ingest_file(file_path: str)`:
  - Add `.webp` to the image extensions filter.
  - Call the structured extraction instead of simple captioning for standalone images.
- Update `ingest_pdf_document(file_path: str)`:
  - Evaluate chunk text length (excluding image refs).
  - Use `fitz` (PyMuPDF) to render scanned pages to PNG bytes in memory.
  - Send bytes to `extract_and_caption_bytes` and combine the resulting text and visual caption.

### 3.2. `ai-chat/main.py`
- Add `webp` to the file uploader supported formats:
  ```python
  uploaded_file = st.file_uploader(
      'Choose a file',
      type=['txt', 'png', 'jpg', 'jpeg', 'webp', 'pdf'],
  )
  ```

---

## 4. Error Handling & Edge Cases
- **Missing PyMuPDF/fitz:** Since `pymupdf4llm` is installed, `fitz` is guaranteed to be available. Fall back gracefully to `pypdf` page extraction if `fitz` import fails.
- **Gemini API Errors / Rate Limits:** Keep the existing exponential backoff retry decorator (`generate_image_caption` retries) for the structured Gemini calls.
- **Zero Extracted Content:** If both `extracted_text` and `visual_caption` are empty, fall back to a placeholder text stating that the page or image was empty.

---

## 5. Testing & Verification

### 5.1. Unit Tests to Add/Modify (`ai-chat/test_parser.py`)
1. `test_webp_ingestion`: Mocking the Gemini client to verify that a WebP file runs through `ingest_file` and generates a structured response.
2. `test_scanned_pdf_page_extraction`: Mocking a PDF where page 1 has no text. Mock PyMuPDF rendering and Gemini response to ensure the OCR text is successfully integrated.
3. `test_hybrid_pdf_page_extraction`: Mocking a PDF where page 1 has digital text and page 2 is scanned, verifying correct page-level routing.

---
