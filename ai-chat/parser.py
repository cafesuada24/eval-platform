import os
import re
import time
from PIL import Image
from google import genai
from pypdf import PdfReader
import pymupdf4llm

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

def generate_image_caption(image_path: str) -> str:
    """Generates a detailed semantic description of the image using Gemini API."""
    client = genai.Client()
    
    try:
        image = Image.open(image_path)
    except Exception as e:
        raise RuntimeError(f"Failed to open image at {image_path}: {e}")
        
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
                contents=[image, prompt]
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

def ingest_pdf_document(file_path: str) -> tuple[str, list[dict]]:
    """Parses a PDF document, extracts images, generates captions, and replaces references inline."""
    pdf_basename = os.path.splitext(os.path.basename(file_path))[0]
    extracted_images_dir = os.path.join("assets/extracted_images", pdf_basename)
    os.makedirs(extracted_images_dir, exist_ok=True)
    
    chunks = pymupdf4llm.to_markdown(
        file_path,
        write_images=True,
        image_path=extracted_images_dir,
        page_chunks=True
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
                        "caption": caption
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
