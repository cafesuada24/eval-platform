from unittest.mock import MagicMock, patch

import pytest
from parser import (
    ExtractionResult,
    extract_and_caption_bytes,
    extract_text_from_pdf_fallback,
    extract_text_from_txt,
    generate_image_caption,
    ingest_file,
    ingest_pdf_document,
)


def test_extract_text_from_txt(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello, this is a test.", encoding="utf-8")
    result = extract_text_from_txt(str(txt_file))
    assert "Hello, this is a test." in result

def test_extract_text_from_pdf_fallback_success():
    mock_page_1 = MagicMock()
    mock_page_1.extract_text.return_value = "This is page 1 text."

    mock_page_2 = MagicMock()
    mock_page_2.extract_text.return_value = "This is page 2 text."

    mock_pdf_reader = MagicMock()
    mock_pdf_reader.pages = [mock_page_1, mock_page_2]

    with patch("parser.PdfReader", return_value=mock_pdf_reader) as mock_reader_class:
        text, images = extract_text_from_pdf_fallback("dummy.pdf")

        mock_reader_class.assert_called_once_with("dummy.pdf")
        assert "<!-- PAGE_1 -->" in text
        assert "This is page 1 text." in text
        assert "<!-- PAGE_2 -->" in text
        assert "This is page 2 text." in text
        assert images == []

def test_extract_text_from_pdf_fallback_failure():
    # Test on a missing/invalid file
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf_fallback("non_existent_file.pdf")

@patch("parser.Image.open")
@patch("parser.genai.Client")
def test_generate_image_caption(mock_genai_client_class, mock_image_open):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "This is a detailed mock description of the image."
    mock_client.models.generate_content.return_value = mock_response

    mock_image = MagicMock()
    mock_image_open.return_value = mock_image

    caption = generate_image_caption("dummy_image.png")

    mock_image_open.assert_called_once_with("dummy_image.png")
    mock_client.models.generate_content.assert_called_once()

    args, kwargs = mock_client.models.generate_content.call_args
    assert kwargs.get("model") == "gemini-3.1-flash-lite"
    contents = kwargs.get("contents")
    assert contents[0] == mock_image
    assert "Analyze this image within the context of a technical document repository." in contents[1]

    assert caption == "This is a detailed mock description of the image."

@patch("parser.time.sleep")
@patch("parser.Image.open")
@patch("parser.genai.Client")
def test_generate_image_caption_rate_limit_retry(mock_genai_client_class, mock_image_open, mock_sleep):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "Success after rate limit."

    mock_client.models.generate_content.side_effect = [
        Exception("API rate limit exceeded (429)"),
        mock_response,
    ]

    mock_image = MagicMock()
    mock_image_open.return_value = mock_image

    caption = generate_image_caption("dummy_image.png")

    assert caption == "Success after rate limit."
    assert mock_client.models.generate_content.call_count == 2
    mock_sleep.assert_called_once_with(1)

@patch("parser.generate_image_caption")
@patch("parser.pymupdf4llm.to_markdown")
@patch("parser.os.rename")
@patch("parser.os.path.exists")
@patch("parser.os.makedirs")
def test_ingest_pdf_document(mock_makedirs, mock_exists, mock_rename, mock_to_markdown, mock_generate_caption):
    mock_to_markdown.return_value = [
        {
            "text": "This is page 1.\nHere is an image: ![](assets/extracted_images/image-page0-0.png)\nAnd another: ![](assets/extracted_images/image-page0-1.png)",
            "metadata": {"page_number": 1},
        },
        {
            "text": "This is page 2.\nNo images here.",
            "metadata": {"page_number": 2},
        },
        {
            "text": "This is page 3.\nLast image: ![](assets/extracted_images/image-page2-0.png)",
            "metadata": {"page_number": 3},
        },
    ]

    mock_exists.return_value = True
    mock_generate_caption.side_effect = [
        "Caption for page 1 img 0",
        "Caption for page 1 img 1",
        "Caption for page 3 img 0",
    ]

    markdown, metadata = ingest_pdf_document("path/to/test_doc.pdf")

    mock_makedirs.assert_called_with("assets/extracted_images/test_doc", exist_ok=True)

    mock_to_markdown.assert_called_once_with(
        "path/to/test_doc.pdf",
        write_images=True,
        image_path="assets/extracted_images/test_doc",
        page_chunks=True,
    )

    rename_calls = mock_rename.call_args_list
    assert len(rename_calls) == 3

    assert rename_calls[0][0][0] == "assets/extracted_images/test_doc/image-page0-0.png"
    assert rename_calls[0][0][1] == "assets/extracted_images/test_doc/test_doc_page_1_img_0.png"

    caption_calls = mock_generate_caption.call_args_list
    assert len(caption_calls) == 3
    assert caption_calls[0][0][0] == "assets/extracted_images/test_doc/test_doc_page_1_img_0.png"

    assert "assets/extracted_images/test_doc/test_doc_page_1_img_0.png" in markdown
    assert "**Image Caption:** Caption for page 1 img 0" in markdown
    assert "assets/extracted_images/test_doc/test_doc_page_1_img_1.png" in markdown
    assert "**Image Caption:** Caption for page 1 img 1" in markdown
    assert "assets/extracted_images/test_doc/test_doc_page_3_img_0.png" in markdown
    assert "**Image Caption:** Caption for page 3 img 0" in markdown

    assert "<!-- PAGE_1 -->" in markdown
    assert "<!-- PAGE_2 -->" in markdown
    assert "<!-- PAGE_3 -->" in markdown

    assert len(metadata) == 3
    assert metadata[0] == {
        "asset_path": "assets/extracted_images/test_doc/test_doc_page_1_img_0.png",
        "page_number": 1,
        "caption": "Caption for page 1 img 0",
    }


@patch("parser.MarkdownTextSplitter")
@patch("parser.add_chunks_to_db")
@patch("parser.generate_embeddings")
@patch("parser.extract_text_from_txt")
def test_ingest_file_txt(mock_extract, mock_embed, mock_add, mock_splitter_class):
    mock_extract.return_value = "Hello World. This is a text file.\n<!-- PAGE_2 -->\nAnother page."
    mock_embed.return_value = [[0.1], [0.2]]

    mock_splitter = MagicMock()
    mock_splitter.split_text.return_value = [
        "Hello World. This is a text file.",
        "<!-- PAGE_2 -->\nAnother page.",
    ]
    mock_splitter_class.return_value = mock_splitter

    count = ingest_file("dummy.txt")
    assert count == 2

    mock_extract.assert_called_once_with("dummy.txt")
    mock_embed.assert_called_once()
    mock_add.assert_called_once()

    args, kwargs = mock_add.call_args
    assert kwargs["source"] == "dummy.txt"
    assert kwargs["chunks"] == ["Hello World. This is a text file.", "<!-- PAGE_2 -->\nAnother page."]
    assert kwargs["metadatas"][0]["page_number"] == 1
    assert kwargs["metadatas"][1]["page_number"] == 2


@patch("parser.add_chunks_to_db")
@patch("parser.generate_embeddings")
@patch("parser.generate_image_caption")
@patch("parser.shutil.copy2")
def test_ingest_file_image(mock_copy2, mock_caption, mock_embed, mock_add, tmp_path):
    mock_caption.return_value = "A cute kitten."
    mock_embed.return_value = [[0.1], [0.2]]

    image_file = tmp_path / "kitten.png"
    image_file.write_text("dummy image data")

    with patch("parser.Path.mkdir") as mock_mkdir:
        count = ingest_file(str(image_file))

    assert count == 2
    mock_caption.assert_called_once()
    mock_copy2.assert_called_once()
    mock_add.assert_called_once()


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
    
    contents = kwargs.get("contents")
    assert len(contents) == 2
    assert contents[1] == "Analyze this document page/image. Perform OCR to extract all readable text exactly, and write a detailed descriptive caption for any charts, diagrams, drawings, or figures."


@patch("parser.time.sleep")
@patch("parser.genai.Client")
def test_extract_and_caption_bytes_failure(mock_genai_client_class, mock_sleep):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    mock_client.models.generate_content.side_effect = Exception("API failure")

    with pytest.raises(Exception) as exc_info:
        extract_and_caption_bytes(b"dummy bytes", "image/png")
    
    assert "API failure" in str(exc_info.value)
    assert mock_client.models.generate_content.call_count == 4
    assert mock_sleep.call_count == 3


