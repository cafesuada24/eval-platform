import os
import json
import shutil
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.engine.orchestrator import FIXTURES_DIR

client = TestClient(app)
TEST_SESSIONS_DIR = os.path.join(FIXTURES_DIR, 'sessions')
TEST_UPLOAD_DIR = os.path.join(FIXTURES_DIR, 'uploads')


@pytest.fixture(autouse=True)
def cleanup_test_sessions():
    """Ensure clean state before and after each test."""
    for path in (TEST_SESSIONS_DIR, TEST_UPLOAD_DIR):
        if os.path.exists(path):
            shutil.rmtree(path)
            
    # Clean and reset the ChromaDB vector database collection for complete test isolation
    try:
        from app.services import rag_service
        try:
            rag_service.chroma_client.delete_collection(rag_service.collection.name)
        except Exception:
            pass
        
        # Recreate fresh collection using MockEmbeddingFunction
        rag_service.collection = rag_service.chroma_client.get_or_create_collection(
            name="uploaded_documents_test",
            embedding_function=rag_service.MockEmbeddingFunction()
        )
    except Exception as e:
        print(f"Failed to reset ChromaDB testing collection: {e}")
        
    yield
    for path in (TEST_SESSIONS_DIR, TEST_UPLOAD_DIR):
        if os.path.exists(path):
            shutil.rmtree(path)


def test_upload_text_file():
    """Test text file upload with direct decoding."""
    response = client.post(
        "/v1/playground/upload",
        files={"file": ("test.txt", b"Hello eval platform text content")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test.txt"
    assert data["text"] == "Hello eval platform text content"
    assert data["id"].startswith("art-")
    assert data["size"] == len(b"Hello eval platform text content")


@patch("app.api.routes.playground.genai.Client")
def test_upload_multimodal_file(mock_genai_client_class):
    """Test PDF/Image upload where text is extracted via Gemini multimodal mock."""
    # Setup mock Client and response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Extracted text content from image/pdf"
    mock_client.models.generate_content.return_value = mock_response
    mock_genai_client_class.return_value = mock_client

    response = client.post(
        "/v1/playground/upload",
        files={"file": ("test_doc.pdf", b"Dummy PDF bytes")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_doc.pdf"
    assert data["text"] == "Extracted text content from image/pdf"
    assert data["id"].startswith("art-")
    assert data["size"] == len(b"Dummy PDF bytes")
    
    mock_client.models.generate_content.assert_called_once()


def test_list_uploaded_files():
    """Test listing uploaded files."""
    # List when empty
    response = client.get("/v1/playground/files")
    assert response.status_code == 200
    assert response.json() == []

    # Upload one
    upload_res = client.post(
        "/v1/playground/upload",
        files={"file": ("test.txt", b"Content")}
    )
    assert upload_res.status_code == 200
    uploaded_data = upload_res.json()

    # List again
    list_res = client.get("/v1/playground/files")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data) == 1
    assert list_data[0]["id"] == uploaded_data["id"]
    assert list_data[0]["name"] == "test.txt"
    assert list_data[0]["text"] == "Content"
    assert list_data[0]["size"] == len(b"Content")


def test_delete_uploaded_file():
    """Test deleting an uploaded file."""
    # Upload one
    upload_res = client.post(
        "/v1/playground/upload",
        files={"file": ("test.txt", b"Content")}
    )
    uploaded_data = upload_res.json()
    file_id = uploaded_data["id"]

    # Delete non-existent
    del_fail = client.delete("/v1/playground/files/nonexistent")
    assert del_fail.status_code == 404

    # Delete actual
    del_ok = client.delete(f"/v1/playground/files/{file_id}")
    assert del_ok.status_code == 200
    assert del_ok.json()["status"] == "success"

    # List should be empty
    list_res = client.get("/v1/playground/files")
    assert list_res.json() == []



@patch("app.api.routes.playground.execute_ai_judge_async")
def test_metric_execution_and_session_logging(mock_execute_judge):
    """Test transient metric execution and verify that the run gets logged into session history."""
    # Setup async mock response for execute_ai_judge_async
    mock_output = MagicMock()
    mock_output.score = 4.5
    mock_output.justification = "The answer is excellent and accurate."
    
    # Using patch with return_value for async/await mock compatibility
    async def mock_async_run(*args, **kwargs):
        return mock_output
    mock_execute_judge.side_effect = mock_async_run

    payload = {
        "metric_config": {
            "name": "test_completeness_judge",
            "type": "ai-judge",
            "description": "Evaluates answer completeness",
            "required_inputs": ["input_text", "output_text"],
            "prompt_template": "Evaluate completeness of: {{ output_text }} given query {{ input_text }}",
            "model_configuration": {
                "provider": "google",
                "model": "gemini-3.1-flash-lite",
                "temperature": 0.1
            },
            "scoring_scale": {
                "min": 1,
                "max": 5,
                "data_type": "integer"
            }
        },
        "inputs": {
            "input_text": "What is the capital of France?",
            "output_text": "The capital of France is Paris."
        },
        "metric_name": "test_completeness_judge"
    }

    response = client.post("/v1/playground/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 4.5
    assert "excellent and accurate" in data["justification"]

    # Verify that the test run message was appended to the session file
    session_file_path = os.path.join(TEST_SESSIONS_DIR, "test_completeness_judge.json")
    assert os.path.exists(session_file_path)

    with open(session_file_path) as f:
        session_data = json.load(f)
        assert session_data["metric_name"] == "test_completeness_judge"
        messages = session_data["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert "[Test Run]" in content
        assert "input_text" in content
        assert "output_text" in content
        assert "Score: 4.5" in content


@patch("app.services.rag_service.pypdf.PdfReader")
def test_upload_pdf_local_extraction(mock_pdf_reader_class):
    """Test PDF upload with pure local text extraction."""
    # Mock pypdf PdfReader and page extraction
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Extracted text content from local PDF using pypdf"
    mock_reader.pages = [mock_page]
    mock_pdf_reader_class.return_value = mock_reader

    response = client.post(
        "/v1/playground/upload",
        files={"file": ("test_local.pdf", b"PDF dummy bytes")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_local.pdf"
    assert data["text"] == "Extracted text content from local PDF using pypdf"
    assert data["id"].startswith("art-")


@patch("app.api.routes.playground.execute_ai_judge_async")
def test_end_to_end_rag_retrieval_and_delete(mock_execute_judge):
    """Test full end-to-end RAG retrieval flow from upload to query retrieval and delete."""
    # Setup mock judge output
    mock_output = MagicMock()
    mock_output.score = 4.0
    mock_output.justification = "Good enough."
    async def mock_async_run(*args, **kwargs):
        return mock_output
    mock_execute_judge.side_effect = mock_async_run

    # 1. Upload a unique document
    unique_text = "The quick brown fox jumps over the lazy dog. ChromaDB vector indexing is fully operational."
    upload_res = client.post(
        "/v1/playground/upload",
        files={"file": ("rag_test.txt", unique_text.encode("utf-8"))}
    )
    assert upload_res.status_code == 200
    uploaded_data = upload_res.json()
    file_id = uploaded_data["id"]

    # 2. Trigger metric execution that requests 'retrieved_context'
    payload = {
        "metric_config": {
            "name": "rag_completeness_judge",
            "type": "ai-judge",
            "description": "Evaluates RAG completeness",
            "required_inputs": ["retrieved_context", "output_text"],
            "prompt_template": "Retrieve context: {{ retrieved_context }} given {{ output_text }}",
            "model_configuration": {
                "provider": "google",
                "model": "gemini-3.1-flash-lite",
                "temperature": 0.1
            },
            "scoring_scale": {
                "min": 1,
                "max": 5,
                "data_type": "integer"
            }
        },
        "inputs": {
            "output_text": "Evaluating fox and dog jumps."
        },
        "metric_name": "rag_completeness_judge"
    }

    test_res = client.post("/v1/playground/test", json=payload)
    assert test_res.status_code == 200
    test_data = test_res.json()
    
    # Verify that the context was retrieved from our uploaded document (not the mock database!)
    retrieved_context = test_data["variables"]["retrieved_context"]
    assert "ChromaDB vector indexing" in retrieved_context
    assert "fox jumps over" in retrieved_context

    # 3. Delete the uploaded file and verify it's removed from ChromaDB
    del_res = client.delete(f"/v1/playground/files/{file_id}")
    assert del_res.status_code == 200

    # 4. Trigger metric execution again and verify it no longer retrieves the document
    test_res_2 = client.post("/v1/playground/test", json=payload)
    assert test_res_2.status_code == 200
    test_data_2 = test_res_2.json()
    retrieved_context_2 = test_data_2["variables"]["retrieved_context"]
    
    # Since ChromaDB is now empty and mock fallback is removed, it should return an empty string
    assert retrieved_context_2 == ""
