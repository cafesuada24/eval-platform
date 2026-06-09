import pytest
from unittest.mock import AsyncMock, patch
from app.core.eval_engine.models import Metric, ModelConfiguration
from app.core.eval_engine.services.multi_step_evaluators import (
    evaluate_faithfulness_rigorous,
    evaluate_answer_relevancy_rigorous,
    evaluate_context_recall_rigorous,
)

def mock_litellm_response(content: str):
    mock_choice = AsyncMock()
    mock_choice.message.content = content
    mock_response = AsyncMock()
    mock_response.choices = [mock_choice]
    mock_response.usage_metadata = AsyncMock(prompt_token_count=10, candidates_token_count=10)
    return mock_response

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_faithfulness_rigorous_success(mock_acompletion):
    # Mock Claim Extraction Step
    mock_extraction = mock_litellm_response('{"claims": ["The model is fast.", "The model has 12 tests."]}')
    # Mock Claim Verification Step
    mock_verification = mock_litellm_response(
        '{"verifications": ['
        '  {"claim": "The model is fast.", "verdict": "supported", "reason": "Doc 1 says it is fast."},'
        '  {"claim": "The model has 12 tests.", "verdict": "supported", "reason": "Doc 2 lists 12 tests."}'
        ']}'
    )
    mock_acompletion.side_effect = [mock_extraction, mock_verification]

    metric = Metric(
        name="faithfulness_rigorous",
        description="F",
        type="ai-judge",
        required_inputs=["retrieved_context", "output_text"],
        model_configuration=ModelConfiguration(provider="openai", model="gpt-4o")
    )
    bindings = {
        "retrieved_context": "Doc 1: The model is fast. Doc 2: The model has 12 tests.",
        "output_text": "The model is fast and has 12 tests."
    }

    result = await evaluate_faithfulness_rigorous(metric, bindings)
    assert result.score == 1.0
    assert any("supported" in item.lower() for item in result.justification)

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_faithfulness_rigorous_empty_claims(mock_acompletion):
    mock_extraction = mock_litellm_response('{"claims": []}')
    mock_acompletion.side_effect = [mock_extraction]

    metric = Metric(
        name="faithfulness_rigorous",
        description="F",
        type="ai-judge",
        required_inputs=["retrieved_context", "output_text"],
        model_configuration=ModelConfiguration(provider="openai", model="gpt-4o")
    )
    bindings = {
        "retrieved_context": "Doc 1: The model is fast. Doc 2: The model has 12 tests.",
        "output_text": "No facts here."
    }

    result = await evaluate_faithfulness_rigorous(metric, bindings)
    assert result.score == 1.0
    assert any("no claims" in item.lower() for item in result.justification)

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_answer_relevancy_rigorous(mock_acompletion):
    mock_extraction = mock_litellm_response('{"statements": ["Paris is in France.", "I like pizza."]}')
    mock_relevance = mock_litellm_response(
        '{"verdicts": ['
        '  {"statement": "Paris is in France.", "relevant": true, "reason": "Directly answers where Paris is."},'
        '  {"statement": "I like pizza.", "relevant": false, "reason": "Irrelevant to France."}'
        ']}'
    )
    mock_acompletion.side_effect = [mock_extraction, mock_relevance]

    metric = Metric(
        name="answer_relevancy_rigorous",
        description="AR",
        type="ai-judge",
        required_inputs=["input_text", "output_text"],
        model_configuration=ModelConfiguration(provider="openai", model="gpt-4o")
    )
    bindings = {
        "input_text": "Tell me about Paris",
        "output_text": "Paris is in France. I like pizza."
    }

    result = await evaluate_answer_relevancy_rigorous(metric, bindings)
    assert result.score == 0.5
    assert any("relevant" in item.lower() for item in result.justification)

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_answer_relevancy_rigorous_empty_statements(mock_acompletion):
    mock_extraction = mock_litellm_response('{"statements": []}')
    mock_acompletion.side_effect = [mock_extraction]

    metric = Metric(
        name="answer_relevancy_rigorous",
        description="AR",
        type="ai-judge",
        required_inputs=["input_text", "output_text"],
        model_configuration=ModelConfiguration(provider="openai", model="gpt-4o")
    )
    bindings = {
        "input_text": "Tell me about Paris",
        "output_text": ""
    }

    result = await evaluate_answer_relevancy_rigorous(metric, bindings)
    assert result.score == 1.0
    assert any("no statements" in item.lower() for item in result.justification)

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_context_recall_rigorous(mock_acompletion):
    mock_extraction = mock_litellm_response('{"claims": ["Fact A", "Fact B"]}')
    mock_recall = mock_litellm_response(
        '{"verdicts": ['
        '  {"claim": "Fact A", "recalled": true, "reason": "Found in Doc 1."},'
        '  {"claim": "Fact B", "recalled": false, "reason": "Not found."}'
        ']}'
    )
    mock_acompletion.side_effect = [mock_extraction, mock_recall]

    metric = Metric(
        name="context_recall_rigorous",
        description="CR",
        type="ai-judge",
        required_inputs=["retrieved_context", "testcase.expected_outputs.expected_output"],
        model_configuration=ModelConfiguration(provider="openai", model="gpt-4o")
    )
    bindings = {
        "retrieved_context": "Fact A is true.",
        "testcase.expected_outputs.expected_output": "Fact A and Fact B"
    }

    result = await evaluate_context_recall_rigorous(metric, bindings)
    assert result.score == 0.5
    assert any("recalled" in item.lower() for item in result.justification)

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_context_recall_rigorous_empty_claims(mock_acompletion):
    mock_extraction = mock_litellm_response('{"claims": []}')
    mock_acompletion.side_effect = [mock_extraction]

    metric = Metric(
        name="context_recall_rigorous",
        description="CR",
        type="ai-judge",
        required_inputs=["retrieved_context", "testcase.expected_outputs.expected_output"],
        model_configuration=ModelConfiguration(provider="openai", model="gpt-4o")
    )
    bindings = {
        "retrieved_context": "Fact A is true.",
        "testcase.expected_outputs.expected_output": ""
    }

    result = await evaluate_context_recall_rigorous(metric, bindings)
    assert result.score == 1.0
    assert any("no claims" in item.lower() for item in result.justification)


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_call_llm_structured_robustness(mock_acompletion):
    from app.core.eval_engine.services.multi_step_evaluators import _call_llm_structured, ClaimsList
    
    # Mock return value wrapped in markdown code blocks
    mock_response = mock_litellm_response('```json\n{"claims": ["Robust claim 1", "Robust claim 2"]}\n```')
    mock_acompletion.return_value = mock_response
    
    metric = Metric(
        name="faithfulness_rigorous",
        description="F",
        type="ai-judge",
        required_inputs=["retrieved_context", "output_text"],
        model_configuration=ModelConfiguration(provider="openai", model="gpt-4o")
    )
    
    result = await _call_llm_structured(
        metric=metric,
        system_prompt="Extract claims.",
        user_prompt="Input text",
        response_schema=ClaimsList
    )
    
    # Assert result is correctly parsed into Pydantic model
    assert isinstance(result, ClaimsList)
    assert result.claims == ["Robust claim 1", "Robust claim 2"]
    
    # Assert system prompt was enhanced with instructions and JSON schema
    called_messages = mock_acompletion.call_args.kwargs["messages"]
    system_message = next(msg for msg in called_messages if msg["role"] == "system")
    assert "You MUST return your output ONLY as a JSON object matching this JSON schema:" in system_message["content"]
    assert '"required": ["claims"]' in system_message["content"]

