from unittest.mock import MagicMock, patch
import pytest
from parser import extract_text_from_txt, extract_text_from_pdf_fallback

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
