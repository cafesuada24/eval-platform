from unittest.mock import MagicMock, patch
import pytest
from app.models.config import MetricConfig, ModelConfiguration, ScoringScale
from app.engine.executor import (
    get_litellm_model_name,
    get_system_instruction,
    execute_ai_judge,
    execute_ai_judge_async
)

@pytest.fixture
def dummy_metric_config():
    return MetricConfig(
        name="test_metric",
        type="ai-judge",
        description="A test metric",
        model_configuration=ModelConfiguration(provider="anthropic", model="claude-3-5-sonnet"),
        required_inputs=["input_text"],
        prompt_template="Test prompt {{ input_text }}",
        scoring_scale=ScoringScale(min=1.0, max=5.0, data_type="integer")
    )

def test_get_litellm_model_name(dummy_metric_config):
    assert get_litellm_model_name(dummy_metric_config) == "anthropic/claude-3-5-sonnet"

    # Already formatted model name should remain unchanged
    dummy_metric_config.model_configuration.model = "anthropic/claude-3"
    assert get_litellm_model_name(dummy_metric_config) == "anthropic/claude-3"

def test_get_system_instruction(dummy_metric_config):
    instruction = get_system_instruction(dummy_metric_config)
    assert "integer" in instruction
    assert "1.0" in instruction
    assert "5.0" in instruction

@patch("app.engine.executor.litellm.completion")
def test_execute_ai_judge(mock_completion, dummy_metric_config):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"score": 4, "justification": "Very good performance."}'))
    ]
    mock_completion.return_value = mock_response

    output = execute_ai_judge(dummy_metric_config, "Test prompt")

    assert output.score == 4.0
    assert output.justification == "Very good performance."

    # Verify litellm parameters
    mock_completion.assert_called_once()
    kwargs = mock_completion.call_args.kwargs
    assert kwargs["model"] == "anthropic/claude-3-5-sonnet"
    assert kwargs["response_format"] == {"type": "json_object"}

@pytest.mark.anyio
@patch("app.engine.executor.litellm.acompletion")
async def test_execute_ai_judge_async(mock_acompletion, dummy_metric_config):
    # Setup async mock response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"score": 3.5, "justification": "Average."}'))
    ]
    mock_acompletion.return_value = mock_response

    output = await execute_ai_judge_async(dummy_metric_config, "Test prompt")

    assert output.score == 3.5
    assert output.justification == "Average."

    mock_acompletion.assert_called_once()
