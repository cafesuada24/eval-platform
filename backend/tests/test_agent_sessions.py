import os
import shutil
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.engine.orchestrator import FIXTURES_DIR

client = TestClient(app)
SESSIONS_DIR = os.path.join(FIXTURES_DIR, 'sessions')
METRICS_DIR = os.path.join(FIXTURES_DIR, 'metrics')


@pytest.fixture(autouse=True)
def clean_dirs():
    """Ensure sessions and metrics directories are clean before and after each test."""
    test_session_file = os.path.join(SESSIONS_DIR, "hallucination_ai_judge.json")
    test_session_file_2 = os.path.join(SESSIONS_DIR, "brand_safety_judge.json")
    test_metric_file = os.path.join(METRICS_DIR, "brand_safety_judge.yaml")

    for f in [test_session_file, test_session_file_2, test_metric_file]:
        if os.path.exists(f):
            os.remove(f)
    yield
    for f in [test_session_file, test_session_file_2, test_metric_file]:
        if os.path.exists(f):
            os.remove(f)


def test_get_non_existent_session():
    """Fetching a session that doesn't exist should return 200 with an empty message list."""
    response = client.get("/v1/agent/sessions/non_existent_metric")
    assert response.status_code == 200
    data = response.json()
    assert data["metric_name"] == "non_existent_metric"
    assert data["messages"] == []


@patch("app.api.routes.agent.MetricAgentService.chat_with_agent")
def test_chat_persistence_and_reload(mock_chat):
    """Test that chatting with a metric_name persists history and reload retrieves it."""
    # Mock the agent service response returning a draft metric
    mock_chat.return_value = {
        "response_text": "Sure, I can help you with hallucination metric.",
        "updated_metric": None
    }

    # Step 1: Send a message to /chat with a metric_name
    chat_payload = {
        "message": "Hello agent, let's build hallucination metric",
        "metric_name": "hallucination_ai_judge"
    }
    response = client.post("/v1/agent/chat", json=chat_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["response_text"] == "Sure, I can help you with hallucination metric."
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hello agent, let's build hallucination metric"
    assert data["messages"][1]["role"] == "model"
    assert data["messages"][1]["content"] == "Sure, I can help you with hallucination metric."

    # Verify that the session JSON file actually exists on disk
    session_file = os.path.join(SESSIONS_DIR, "hallucination_ai_judge.json")
    assert os.path.exists(session_file)

    # Step 2: Reload session via GET endpoint
    response_get = client.get("/v1/agent/sessions/hallucination_ai_judge")
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert data_get["metric_name"] == "hallucination_ai_judge"
    assert len(data_get["messages"]) == 2
    assert data_get["messages"][0]["role"] == "user"
    assert data_get["messages"][0]["content"] == "Hello agent, let's build hallucination metric"

    # Step 3: Send a second message and assert that the history was loaded and appended
    mock_chat.reset_mock()
    mock_chat.return_value = {
        "response_text": "I have added required inputs.",
        "updated_metric": None
    }
    chat_payload_2 = {
        "message": "Add output_text as required input",
        "metric_name": "hallucination_ai_judge"
    }
    response_chat2 = client.post("/v1/agent/chat", json=chat_payload_2)
    assert response_chat2.status_code == 200
    data_chat2 = response_chat2.json()
    assert len(data_chat2["messages"]) == 4  # user1, model1, user2, model2
    assert data_chat2["messages"][2]["content"] == "Add output_text as required input"
    assert data_chat2["messages"][3]["content"] == "I have added required inputs."

    # Step 4: Clear the session using DELETE
    response_del = client.delete("/v1/agent/sessions/hallucination_ai_judge")
    assert response_del.status_code == 200
    assert response_del.json()["status"] == "success"

    # Verify reload after DELETE returns empty list
    response_get_cleared = client.get("/v1/agent/sessions/hallucination_ai_judge")
    assert response_get_cleared.status_code == 200
    assert response_get_cleared.json()["messages"] == []


@patch("app.api.routes.agent.MetricAgentService.chat_with_agent")
def test_chat_without_persistence_backwards_compatibility(mock_chat):
    """Test that chatting without metric_name doesn't persist and respects standard inputs."""
    mock_chat.return_value = {
        "response_text": "Stateless response",
        "updated_metric": None
    }

    # Pass full messages directly
    chat_payload = {
        "messages": [
            {"role": "user", "content": "Stateless ping"}
        ]
    }
    response = client.post("/v1/agent/chat", json=chat_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["response_text"] == "Stateless response"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["content"] == "Stateless ping"
    assert data["messages"][1]["content"] == "Stateless response"

    # Assert no session files were created
    session_file = os.path.join(SESSIONS_DIR, "stateless.json")
    assert not os.path.exists(session_file)


def test_chat_missing_inputs_error():
    """Assert 400 error is raised if both message and messages list are missing."""
    response = client.post("/v1/agent/chat", json={"metric_name": "test_metric"})
    assert response.status_code == 400
    assert "No message or message history" in response.json()["detail"]


@patch("app.api.routes.agent.MetricAgentService.chat_with_agent")
def test_chat_null_metric_with_new_metric_creation(mock_chat):
    """Test that chatting with metric_name=None which results in a draft metric creation
    persists history under the new metric name but does NOT save the YAML file to the metrics config yet."""
    mock_chat.return_value = {
        "response_text": "I have created the metric for you.",
        "updated_metric": {
            "name": "brand_safety_judge",
            "type": "ai-judge",
            "description": "Brand safety check",
            "model_configuration": {"provider": "google", "model": "gemini"},
            "required_inputs": ["output_text"],
            "prompt_template": "Check brand safety",
            "scoring_scale": {"min": 0.0, "max": 1.0, "data_type": "integer"}
        }
    }

    chat_payload = {
        "message": "Create a brand safety metric called brand_safety_judge",
        "metric_name": None
    }
    response = client.post("/v1/agent/chat", json=chat_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["updated_metric"]["name"] == "brand_safety_judge"

    # Ensure the yaml config is NOT automatically saved to the metrics directory (draft status)
    metric_file = os.path.join(METRICS_DIR, "brand_safety_judge.yaml")
    assert not os.path.exists(metric_file)

    # Assert that the session WAS persisted under the new metric name
    session_file = os.path.join(SESSIONS_DIR, "brand_safety_judge.json")
    assert os.path.exists(session_file)

    # Reload using GET
    response_get = client.get("/v1/agent/sessions/brand_safety_judge")
    assert response_get.status_code == 200
    assert len(response_get.json()["messages"]) == 2
    assert response_get.json()["messages"][0]["content"] == "Create a brand safety metric called brand_safety_judge"
    assert response_get.json()["messages"][1]["content"] == "I have created the metric for you."
