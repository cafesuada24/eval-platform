from unittest.mock import MagicMock, patch
import json
import pytest
from app.services.metric_agent import MetricAgentService


@patch("app.services.metric_agent.genai.Client")
def test_metric_agent_service_initialization(mock_client_class):
    service = MetricAgentService(api_key="fake-key")
    mock_client_class.assert_called_once_with(api_key="fake-key")


@patch("app.services.metric_agent.genai.Client")
def test_chat_with_agent_structured_output_no_metric(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "response_text": "Hello! I can help you build metrics.",
        "updated_metric": None
    })
    mock_client.models.generate_content.return_value = mock_response

    service = MetricAgentService(api_key="fake-key")
    messages = [{"role": "user", "content": "Hello agent!"}]

    result = service.chat_with_agent(messages)

    assert result["response_text"] == "Hello! I can help you build metrics."
    assert result["updated_metric"] is None

    mock_client.models.generate_content.assert_called_once()
    kwargs = mock_client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-3.1-flash-lite"
    assert "input_text" in kwargs["config"].system_instruction
    assert kwargs["config"].response_mime_type == "application/json"


@patch("app.services.metric_agent.genai.Client")
def test_chat_with_agent_structured_output_with_draft_metric(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "response_text": "I have created the draft metric config.",
        "updated_metric": {
            "name": "hallucination_ai_judge",
            "type": "ai-judge",
            "description": "Groundedness check",
            "model_configuration": {"provider": "anthropic", "model": "claude"},
            "required_inputs": ["output_text", "retrieved_context"],
            "prompt_template": "Analyze Statements",
            "scoring_scale": {"min": 1.0, "max": 5.0, "data_type": "integer"}
        }
    })
    mock_client.models.generate_content.return_value = mock_response

    service = MetricAgentService(api_key="fake-key")
    messages = [{"role": "user", "content": "Create a hallucination judge metric"}]

    result = service.chat_with_agent(messages)

    assert result["response_text"] == "I have created the draft metric config."
    assert result["updated_metric"]["name"] == "hallucination_ai_judge"
    assert result["updated_metric"]["type"] == "ai-judge"
    assert result["updated_metric"]["model_configuration"]["provider"] == "anthropic"
