import pytest
from unittest.mock import AsyncMock, patch
from app.core.eval_engine.models import Metric, EvaluationContext, TestCase, ModelConfiguration
from app.core.eval_engine.services.metric_evaluator import MetricEvaluatorService

@pytest.mark.asyncio
@patch("app.core.eval_engine.services.metric_evaluator.evaluate_faithfulness_rigorous")
async def test_routing_in_evaluator_service(mock_evaluate_faithfulness):
    from app.core.eval_engine.models import MetricRunResult, AssertionStatus, JudgeResult
    
    mock_evaluate_faithfulness.return_value = JudgeResult(
        score=0.9,
        justification=["Factual accuracy high."],
        evidence=["Claim A is supported."],
        improvements=None
    )

    rs_extractor = AsyncMock()
    rs_extractor.extract_variable.side_effect = lambda variable, context: "some_value"
    
    evaluator = MetricEvaluatorService(
        rs_extractor=rs_extractor,
        formula_evaluator=AsyncMock(),
        ai_judge_service=AsyncMock()
    )

    metric = Metric(
        name="faithfulness_rigorous",
        description="F",
        type="ai-judge",
        required_inputs=["retrieved_context", "output_text"],
        evaluation_strategy="faithfulness_rigorous",
        model_configuration=ModelConfiguration(provider="openai", model="gpt-4o")
    )
    context = EvaluationContext(
        test_case=TestCase(id=None, inputs={}, expected_outputs={}, metadata={}),
        runtime_states=[]
    )

    result = await evaluator.evaluate(metric, context)
    assert result.score == 0.9
    assert result.justification == "Factual accuracy high."
    assert result.assertion_status == AssertionStatus.PASS
    mock_evaluate_faithfulness.assert_called_once()
