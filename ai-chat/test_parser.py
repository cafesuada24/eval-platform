from unittest.mock import MagicMock, patch
import pytest
from parser import extract_text_from_txt, extract_text_from_pdf_fallback, generate_image_caption, ingest_pdf_document

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
    with pytest.raises(Exception):
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
        mock_response
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
            "metadata": {"page_number": 1}
        },
        {
            "text": "This is page 2.\nNo images here.",
            "metadata": {"page_number": 2}
        },
        {
            "text": "This is page 3.\nLast image: ![](assets/extracted_images/image-page2-0.png)",
            "metadata": {"page_number": 3}
        }
    ]
    
    mock_exists.return_value = True
    mock_generate_caption.side_effect = [
        "Caption for page 1 img 0",
        "Caption for page 1 img 1",
        "Caption for page 3 img 0"
    ]
    
    markdown, metadata = ingest_pdf_document("path/to/test_doc.pdf")
    
    mock_makedirs.assert_called_with("assets/extracted_images/test_doc", exist_ok=True)
    
    mock_to_markdown.assert_called_once_with(
        "path/to/test_doc.pdf",
        write_images=True,
        image_path="assets/extracted_images/test_doc",
        page_chunks=True
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
        "caption": "Caption for page 1 img 0"
    }
