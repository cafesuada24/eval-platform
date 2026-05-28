from unittest.mock import MagicMock, patch
import pytest
from app.services.metric_agent import MetricAgentService, UpdateMetricConfigTool

@patch("app.services.metric_agent.genai.Client")
def test_metric_agent_service_initialization(mock_client_class):
    service = MetricAgentService(api_key="fake-key")
    mock_client_class.assert_called_once_with(api_key="fake-key")

@patch("app.services.metric_agent.genai.Client")
def test_chat_with_agent_no_tool_call(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "Hello! I can help you build metrics."
    mock_client.models.generate_content.return_value = mock_response

    service = MetricAgentService(api_key="fake-key")
    messages = [{"role": "user", "content": "Hello agent!"}]

    result = service.chat_with_agent(messages)

    assert result["response_text"] == "Hello! I can help you build metrics."
    assert result["called_tool_args"] == []

    # Verify that generate_content was called correctly
    mock_client.models.generate_content.assert_called_once()
    kwargs = mock_client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-2.5-flash"
    assert "input_text" in kwargs["config"].system_instruction

@patch("app.services.metric_agent.genai.Client")
def test_chat_with_agent_with_tool_call(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "I have created the metric configuration."
    mock_client.models.generate_content.return_value = mock_response

    service = MetricAgentService(api_key="fake-key")
    messages = [{"role": "user", "content": "Create a metric for hallucination"}]

    result = service.chat_with_agent(messages)
    mock_client.models.generate_content.assert_called_once()
    config = mock_client.models.generate_content.call_args.kwargs["config"]

    # Extract the tool function from config
    update_tool = config.tools[0]

    # Test the tool with a valid payload
    res = update_tool(
        name="hallucination_ai_judge",
        type="ai-judge",
        description="Groundedness check",
        model_configuration={"provider": "anthropic", "model": "claude"},
        required_inputs=["output_text", "retrieved_context"],
        prompt_template="Analyze Statements",
        scoring_scale={"min": 1.0, "max": 5.0, "data_type": "integer"}
    )
    assert res == "Success: Metric configuration successfully updated."

    # Test the tool with an invalid required variable
    res_err = update_tool(
        name="hallucination_ai_judge",
        type="ai-judge",
        description="Groundedness check",
        model_configuration={"provider": "anthropic", "model": "claude"},
        required_inputs=["output_text", "invalid_var"],
        prompt_template="Analyze Statements",
        scoring_scale={"min": 1.0, "max": 5.0, "data_type": "integer"}
    )
    assert "Error: Variable 'invalid_var' is not supported" in res_err
