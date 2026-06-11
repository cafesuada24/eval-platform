"""Parser module for file ingestion, PDF text/image extraction, and captioning."""

import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import pymupdf4llm  # type: ignore[import-untyped]
from embedder import generate_embeddings
from google import genai
from langchain_text_splitters import MarkdownTextSplitter
from PIL import Image
from pydantic import BaseModel, Field
from pypdf import PdfReader
from vector_store import add_chunks_to_db


def extract_text_from_txt(file_path: str) -> str:
    """Reads and returns the contents of a text file."""
    with open(file_path, encoding="utf-8") as f:
        return f.read()

def extract_text_from_pdf_fallback(file_path: str) -> tuple[str, list[dict[str, Any]]]:
    """Fallback parser extracting text page-by-page using pypdf."""
    pdf_reader = PdfReader(file_path)
    unified_markdown_parts = []
    for page_idx, page in enumerate(pdf_reader.pages):
        page_num = page_idx + 1
        page_text = page.extract_text() or ""
        page_marker = f"\n\n<!-- PAGE_{page_num} -->\n\n"
        unified_markdown_parts.append(page_marker + page_text)
    return "".join(unified_markdown_parts), []

def generate_image_caption(image_path: str) -> str:
    """Generates a detailed semantic description of the image using Gemini API."""
    client = genai.Client()

    try:
        image = Image.open(image_path)
    except Exception as e:
        raise RuntimeError(f"Failed to open image at {image_path}: {e}") from e

    prompt = (
        "Analyze this image within the context of a technical document repository. "
        "Provide a highly detailed, dense semantic description, captioning all visual charts, "
        "figures, text within images, and structural meaning. Output purely descriptive text."
    )

    max_retries = 3
    wait_time = 1
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=[image, prompt],  # type: ignore[arg-type]
            )
            if response and response.text:
                return response.text.strip()
            raise ValueError("Empty response received from GenAI model.")
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(wait_time)
            wait_time *= 2
    return ""


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
                print(f"Failed to extract and caption bytes after {max_retries} retries: {e}")
                raise e
            time.sleep(wait_time)
            wait_time *= 2



def ingest_pdf_document(file_path: str) -> tuple[str, list[dict[str, Any]]]:
    """Parses a PDF document, extracts images, generates captions, and replaces references inline."""
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

    for page_idx, chunk in enumerate(chunks):
        page_num = chunk.get("metadata", {}).get("page_number", page_idx + 1)
        page_text = chunk.get("text", "")

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
                        caption = generate_image_caption(dest_path)
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

    return "".join(unified_markdown_parts), images_metadata


def ingest_file(file_path: str) -> int:
    """Ingests a file, generates embeddings, stores chunks in ChromaDB, and returns chunk count."""
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[-1].lower()
    images_metadata: list[dict[str, Any]] = []

    if ext == ".txt":
        markdown_text = extract_text_from_txt(file_path)
    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        standalone_dir = Path("assets/extracted_images/standalone")
        standalone_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        dest_path = standalone_dir / unique_filename

        shutil.copy2(file_path, dest_path)

        try:
            caption = generate_image_caption(str(dest_path))
        except Exception as caption_err:
            print(f"Failed to generate caption for {dest_path}: {caption_err}")
            caption = "[Image caption generation failed]"

        markdown_text = f"**Standalone Image Caption ({filename}):** {caption}"
        images_metadata = [{
            "asset_path": str(dest_path.resolve().absolute()),
            "page_number": 1,
            "caption": caption,
        }]
    elif ext == ".pdf":
        markdown_text, images_metadata = ingest_pdf_document(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=100)
    split_chunks = splitter.split_text(markdown_text)

    final_chunks = []
    final_metadatas = []

    current_page = 1
    for chunk in split_chunks:
        # Detect page number
        page_matches = re.findall(r"<!-- PAGE_(\d+) -->", chunk)
        if page_matches:
            current_page = int(page_matches[-1])

        content_type = "table" if "|" in chunk else "text"

        final_chunks.append(chunk)
        final_metadatas.append({
            "source_file": filename,
            "page_number": current_page,
            "content_type": content_type,
        })

    for img_info in images_metadata:
        final_chunks.append(img_info["caption"])
        final_metadatas.append({
            "source_file": filename,
            "page_number": img_info["page_number"],
            "content_type": "image_caption",
            "asset_path": img_info["asset_path"],
        })

    embeddings = generate_embeddings(final_chunks)

    add_chunks_to_db(
        chunks=final_chunks,
        embeddings=embeddings,
        metadatas=final_metadatas,
        source=filename,
    )

    return len(final_chunks)
