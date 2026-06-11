# Hybrid OCR and Captioning Pipeline Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement page-by-page hybrid OCR and captioning ingestion for PDFs and WebP images in the `ai-chat` application.

**Architecture:** 
We will update `parser.py` to use PyMuPDF (`fitz`) to render empty/scanned PDF pages in memory to PNG bytes, and send them to the Gemini API using Pydantic structured output (`gemini-3.1-flash-lite`) to retrieve both raw text and visual captions in a single request. Standalone and embedded images (including WebP) will also use this structured extraction.

**Tech Stack:** Python 3.12, PyMuPDF (fitz), google-genai SDK, Pydantic, Streamlit.

---

### Task 1: WebP Image Format Support

**Files:**
- Modify: [main.py](file:///home/serein/SourceCodes/eval-platform/ai-chat/main.py#L39-L42)
- Modify: [parser.py](file:///home/serein/SourceCodes/eval-platform/ai-chat/parser.py#L140-L141)
- Test: [test_parser.py](file:///home/serein/SourceCodes/eval-platform/ai-chat/test_parser.py#L191-L209)

- [ ] **Step 1: Write the failing test**
  Add the following test to `test_parser.py`:
  ```python
  @patch("parser.add_chunks_to_db")
  @patch("parser.generate_embeddings")
  @patch("parser.generate_image_caption")
  @patch("parser.shutil.copy2")
  def test_ingest_file_webp(mock_copy2, mock_caption, mock_embed, mock_add, tmp_path):
      mock_caption.return_value = "A gorgeous sunset."
      mock_embed.return_value = [[0.15], [0.25]]

      webp_file = tmp_path / "sunset.webp"
      webp_file.write_text("fake webp bytes")

      with patch("parser.Path.mkdir"):
          count = ingest_file(str(webp_file))

      assert count == 2
      mock_caption.assert_called_once()
      mock_copy2.assert_called_once()
      mock_add.assert_called_once()
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `../.venv/bin/pytest -k test_ingest_file_webp`
  Expected: Fail with `ValueError: Unsupported file type: .webp`

- [ ] **Step 3: Write minimal implementation**
  In `ai-chat/main.py`:
  ```python
      uploaded_file = st.file_uploader(
          'Choose a file',
          type=['txt', 'png', 'jpg', 'jpeg', 'webp', 'pdf'],
      )
  ```
  In `ai-chat/parser.py`:
  ```python
      elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `../.venv/bin/pytest -k test_ingest_file_webp`
  Expected: PASS

- [ ] **Step 5: Commit changes**
  ```bash
  git add ai-chat/main.py ai-chat/parser.py ai-chat/test_parser.py
  git commit -m "feat: add support for WebP image file ingestion"
  ```

---

### Task 2: Structured Extraction Helper

**Files:**
- Modify: [parser.py](file:///home/serein/SourceCodes/eval-platform/ai-chat/parser.py#L36)
- Test: [test_parser.py](file:///home/serein/SourceCodes/eval-platform/ai-chat/test_parser.py#L44-L68)

- [ ] **Step 1: Write the failing test**
  Add the following test to `test_parser.py`:
  ```python
  from parser import ExtractionResult, extract_and_caption_bytes

  @patch("parser.genai.Client")
  def test_extract_and_caption_bytes(mock_genai_client_class):
      mock_client = MagicMock()
      mock_genai_client_class.return_value = mock_client

      mock_response = MagicMock()
      mock_response.text = '{"extracted_text": "Important text content", "visual_caption": "Flowchart diagram explanation"}'
      mock_client.models.generate_content.return_value = mock_response

      result = extract_and_caption_bytes(b"dummy bytes", "image/png")
      assert result.extracted_text == "Important text content"
      assert result.visual_caption == "Flowchart diagram explanation"

      args, kwargs = mock_client.models.generate_content.call_args
      assert kwargs.get("model") == "gemini-3.1-flash-lite"
      assert kwargs.get("config").response_mime_type == "application/json"
      assert kwargs.get("config").response_schema == ExtractionResult
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `../.venv/bin/pytest -k test_extract_and_caption_bytes`
  Expected: Fail with `ImportError: cannot import name 'extract_and_caption_bytes'`

- [ ] **Step 3: Write minimal implementation**
  In `ai-chat/parser.py`, add the Pydantic schema and helper function:
  ```python
  from pydantic import BaseModel, Field

  class ExtractionResult(BaseModel):
      extracted_text: str = Field(
          description="The exact raw text extracted from the document page/image. Preserve structure where appropriate."
      )
      visual_caption: str = Field(
          description="A detailed description/caption of any charts, drawings, flowcharts, or visual components present. Leave empty if none."
      )

  def extract_and_caption_bytes(image_bytes: bytes, mime_type: str) -> ExtractionResult:
      """Uses Gemini API to perform both OCR (raw text extraction) and visual captioning in one structured response."""
      client = genai.Client()

      prompt = (
          "Analyze this document page/image. Perform OCR to extract all readable text exactly, "
          "and write a detailed descriptive caption for any charts, diagrams, drawings, or figures."
      )

      max_retries = 3
      wait_time = 1
      for attempt in range(max_retries + 1):
          try:
              response = client.models.generate_content(
                  model="gemini-3.1-flash-lite",
                  contents=[
                      genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                      prompt,
                  ],
                  config=genai.types.GenerateContentConfig(
                      response_mime_type="application/json",
                      response_schema=ExtractionResult,
                  )
              )
              if response and response.text:
                  return ExtractionResult.model_validate_json(response.text.strip())
              raise ValueError("Empty response received from GenAI model.")
          except Exception as e:
              if attempt == max_retries:
                  raise e
              time.sleep(wait_time)
              wait_time *= 2
      return ExtractionResult(extracted_text="", visual_caption="")
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `../.venv/bin/pytest -k test_extract_and_caption_bytes`
  Expected: PASS

- [ ] **Step 5: Commit changes**
  ```bash
  git add ai-chat/parser.py ai-chat/test_parser.py
  git commit -m "feat: implement structured OCR and captioning helper"
  ```

---

### Task 3: Refactor Standalone Image Ingestion

**Files:**
- Modify: [parser.py](file:///home/serein/SourceCodes/eval-platform/ai-chat/parser.py#L140-L160)
- Test: [test_parser.py](file:///home/serein/SourceCodes/eval-platform/ai-chat/test_parser.py#L191-L209)

- [ ] **Step 1: Write the failing test**
  Modify `test_ingest_file_image` in `test_parser.py` (and update `test_ingest_file_webp`) to assert that both raw extracted text and visual captions are indexed:
  ```python
  @patch("parser.add_chunks_to_db")
  @patch("parser.generate_embeddings")
  @patch("parser.extract_and_caption_bytes")
  @patch("parser.shutil.copy2")
  def test_ingest_file_image(mock_copy2, mock_extract, mock_embed, mock_add, tmp_path):
      mock_extract.return_value = ExtractionResult(
          extracted_text="Invoice #1234\nTotal: $50.00",
          visual_caption="A scan of a business invoice receipt."
      )
      mock_embed.return_value = [[0.1], [0.2], [0.3]]

      image_file = tmp_path / "invoice.png"
      image_file.write_text("dummy image data")

      with patch("parser.Path.mkdir"):
          count = ingest_file(str(image_file))

      assert count == 3
      mock_extract.assert_called_once_with(b"dummy image data", "image/png")
      mock_add.assert_called_once()
      args, kwargs = mock_add.call_args
      assert "Invoice #1234" in kwargs["chunks"][0]
      assert "A scan of a business invoice receipt." in kwargs["chunks"][1]
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `../.venv/bin/pytest -k test_ingest_file_image`
  Expected: Fail due to `mock_extract` call differences or assertion failures.

- [ ] **Step 3: Write minimal implementation**
  In `ai-chat/parser.py`, update `ingest_file` image branch:
  ```python
      elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
          standalone_dir = Path("assets/extracted_images/standalone")
          standalone_dir.mkdir(parents=True, exist_ok=True)

          unique_filename = f"{uuid.uuid4().hex}_{filename}"
          dest_path = standalone_dir / unique_filename

          shutil.copy2(file_path, dest_path)

          # Determine mime type
          mime_type = "image/png"
          if ext == ".webp":
              mime_type = "image/webp"
          elif ext in [".jpg", ".jpeg"]:
              mime_type = "image/jpeg"

          with open(file_path, "rb") as img_f:
              img_bytes = img_f.read()

          try:
              result = extract_and_caption_bytes(img_bytes, mime_type)
          except Exception as caption_err:
              print(f"Failed to extract text/caption for {dest_path}: {caption_err}")
              result = ExtractionResult(extracted_text="", visual_caption="[Extraction failed]")

          extracted_txt = result.extracted_text
          visual_cap = result.visual_caption

          markdown_parts = []
          if extracted_txt.strip():
              markdown_parts.append(f"**Extracted Text from Image ({filename}):**\n{extracted_txt}")
          if visual_cap.strip():
              markdown_parts.append(f"**Image Caption ({filename}):** {visual_cap}")

          markdown_text = "\n\n".join(markdown_parts) if markdown_parts else f"[Empty image: {filename}]"
          images_metadata = [{
              "asset_path": str(dest_path.resolve().absolute()),
              "page_number": 1,
              "caption": visual_cap,
          }]
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `../.venv/bin/pytest -k test_ingest_file_image`
  Expected: PASS

- [ ] **Step 5: Commit changes**
  ```bash
  git add ai-chat/parser.py ai-chat/test_parser.py
  git commit -m "refactor: update standalone image ingestion to use structured OCR + Captioning"
  ```

---

### Task 4: Hybrid PDF Ingestion Page-by-Page OCR

**Files:**
- Modify: [parser.py](file:///home/serein/SourceCodes/eval-platform/ai-chat/parser.py#L69-L129) (`ingest_pdf_document`)
- Test: [test_parser.py](file:///home/serein/SourceCodes/eval-platform/ai-chat/test_parser.py#L99-L160)

- [ ] **Step 1: Write the failing test**
  Add a test to verify scanned page fallback and extraction:
  ```python
  import fitz

  @patch("parser.extract_and_caption_bytes")
  @patch("parser.fitz.open")
  @patch("parser.pymupdf4llm.to_markdown")
  @patch("parser.os.makedirs")
  def test_ingest_pdf_document_scanned(mock_makedirs, mock_to_markdown, mock_fitz_open, mock_extract):
      # Mock pymupdf4llm to return a page chunk with empty text (scanned PDF)
      mock_to_markdown.return_value = [
          {
              "text": "",
              "metadata": {"page_number": 1},
          }
      ]
      
      # Mock fitz opening and page rendering
      mock_doc = MagicMock()
      mock_page = MagicMock()
      mock_pixmap = MagicMock()
      mock_pixmap.tobytes.return_value = b"fake scanned page png"
      mock_page.get_pixmap.return_value = mock_pixmap
      mock_doc.__len__.return_value = 1
      mock_doc.__getitem__.return_value = mock_page
      mock_fitz_open.return_value = mock_doc

      # Mock Gemini extraction
      mock_extract.return_value = ExtractionResult(
          extracted_text="OCR Scanned Content",
          visual_caption="Scanned document page description"
      )

      markdown, metadata = ingest_pdf_document("path/to/scanned.pdf")

      mock_fitz_open.assert_called_once_with("path/to/scanned.pdf")
      mock_page.get_pixmap.assert_called_once_with(dpi=150)
      mock_extract.assert_called_once_with(b"fake scanned page png", "image/png")

      assert "OCR Scanned Content" in markdown
      assert "Scanned document page description" in markdown
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `../.venv/bin/pytest -k test_ingest_pdf_document_scanned`
  Expected: Fail (since `ingest_pdf_document` does not currently open fitz or run OCR on empty text chunks).

- [ ] **Step 3: Write minimal implementation**
  Update `ingest_pdf_document` in `ai-chat/parser.py`:
  ```python
  import fitz  # type: ignore[import-untyped]

  def ingest_pdf_document(file_path: str) -> tuple[str, list[dict[str, Any]]]:
      """Parses a PDF document, extracts images, generates captions, and replaces references inline. Runs page-level OCR for scanned/empty pages."""
      pdf_basename = os.path.splitext(os.path.basename(file_path))[0]
      extracted_images_dir = os.path.join("assets/extracted_images", pdf_basename)
      os.makedirs(extracted_images_dir, exist_ok=True)

      chunks = pymupdf4llm.to_markdown(
          file_path,
          write_images=True,
          image_path=extracted_images_dir,
          page_chunks=True,
      )

      images_metadata = []
      unified_markdown_parts = []

      img_pattern = re.compile(r"!\[.*?\]\(([^)]+)\)")
      
      # Open document via fitz for dynamic page rendering on scanned pages
      doc_fitz = None

      for page_idx, chunk in enumerate(chunks):
          page_num = chunk.get("metadata", {}).get("page_number", page_idx + 1)
          page_text = chunk.get("text", "")

          # Check if the page is scanned (i.e. contains no actual text content after removing image tags and whitespace)
          clean_text = img_pattern.sub("", page_text).strip()
          
          if len(clean_text) < 100:
              # Scanned page - render page to image and perform OCR + captioning
              try:
                  if doc_fitz is None:
                      doc_fitz = fitz.open(file_path)
                  
                  if page_num - 1 < len(doc_fitz):
                      page_fitz = doc_fitz[page_num - 1]
                      pix = page_fitz.get_pixmap(dpi=150)
                      img_bytes = pix.tobytes("png")
                      
                      ocr_result = extract_and_caption_bytes(img_bytes, "image/png")
                      
                      ocr_text = ocr_result.extracted_text
                      ocr_caption = ocr_result.visual_caption
                      
                      page_parts = []
                      if ocr_text.strip():
                          page_parts.append(ocr_text)
                      if ocr_caption.strip():
                          page_parts.append(f"**Page Caption/Visual Elements:** {ocr_caption}")
                      
                      if page_parts:
                          page_text = "\n\n".join(page_parts)
              except Exception as ocr_err:
                  print(f"Failed to perform page-level OCR on page {page_num}: {ocr_err}")

          # Process any embedded images extracted by pymupdf4llm
          matches = img_pattern.findall(page_text)

          for index, img_ref in enumerate(matches):
              _, ext = os.path.splitext(img_ref)
              basename = os.path.basename(img_ref)
              src_path = os.path.join(extracted_images_dir, basename)

              new_filename = f"{pdf_basename}_page_{page_num}_img_{index}{ext}"
              dest_path = os.path.join(extracted_images_dir, new_filename)

              caption = ""
              if os.path.exists(src_path):
                  try:
                      os.rename(src_path, dest_path)
                      try:
                          with open(dest_path, "rb") as img_f:
                              img_bytes = img_f.read()
                          
                          # Determine mime type
                          mime_type = "image/png"
                          if ext == ".webp":
                              mime_type = "image/webp"
                          elif ext in [".jpg", ".jpeg"]:
                              mime_type = "image/jpeg"
                              
                          caption_res = extract_and_caption_bytes(img_bytes, mime_type)
                          caption = caption_res.visual_caption or caption_res.extracted_text or "[Image caption empty]"
                      except Exception as caption_err:
                          print(f"Failed to generate caption for {dest_path}: {caption_err}")
                          caption = "[Image caption generation failed]"

                      images_metadata.append({
                          "asset_path": dest_path,
                          "page_number": page_num,
                          "caption": caption,
                      })
                  except Exception as file_err:
                      print(f"Failed to rename file {src_path} to {dest_path}: {file_err}")

              # Find the actual ref string to replace. Since alt text can vary, we search for the specific match
              ref_match = re.search(r"!\[.*?\]\(" + re.escape(img_ref) + r"\)", page_text)
              if ref_match:
                  old_ref_str = ref_match.group(0)
                  new_ref_str = f"![]({dest_path})\n\n**Image Caption:** {caption}"
                  page_text = page_text.replace(old_ref_str, new_ref_str, 1)

          page_marker = f"\n\n<!-- PAGE_{page_num} -->\n\n"
          unified_markdown_parts.append(page_marker + page_text)

      if doc_fitz is not None:
          doc_fitz.close()

      return "".join(unified_markdown_parts), images_metadata
  ```

- [ ] **Step 4: Run test to verify it passes**
  Run: `../.venv/bin/pytest -k test_ingest_pdf_document_scanned`
  Expected: PASS
  
  Run all parser tests: `../.venv/bin/pytest test_parser.py`
  Expected: PASS (8 existing tests + 3 new tests)

- [ ] **Step 5: Commit changes**
  ```bash
  git add ai-chat/parser.py ai-chat/test_parser.py
  git commit -m "feat: implement page-by-page scanned PDF detection and Dynamic OCR"
  ```

---
