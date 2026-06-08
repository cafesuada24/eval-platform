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


@pytest.mark.asyncio
@patch("app.core.eval_engine.services.metric_evaluator.evaluate_faithfulness_rigorous")
async def test_routing_evaluates_thresholds_appropriately(mock_evaluate_faithfulness):
    from app.core.eval_engine.models import MetricThreshold, AssertionStatus, JudgeResult
    
    mock_evaluate_faithfulness.return_value = JudgeResult(
        score=0.4,
        justification=["Factual accuracy low."],
        evidence=["Claim A is refuted."],
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
    )
    context = EvaluationContext(
        test_case=TestCase(id=None, inputs={}, expected_outputs={}, metadata={}),
        runtime_states=[]
    )

    # Test threshold breach: fail_below=0.5
    threshold = MetricThreshold(fail_below=0.5)
    result = await evaluator.evaluate(metric, context, threshold=threshold)
    assert result.score == 0.4
    assert result.assertion_status == AssertionStatus.FAIL

    # Test threshold breach: warning_below=0.6
    threshold = MetricThreshold(warning_below=0.6)
    result = await evaluator.evaluate(metric, context, threshold=threshold)
    assert result.score == 0.4
    assert result.assertion_status == AssertionStatus.WARNING


@pytest.mark.asyncio
@patch("app.core.eval_engine.services.metric_evaluator.evaluate_faithfulness_rigorous")
async def test_routing_handles_exceptions(mock_evaluate_faithfulness):
    from app.core.eval_engine.models import AssertionStatus
    
    mock_evaluate_faithfulness.side_effect = Exception("LLM call failed")

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
    )
    context = EvaluationContext(
        test_case=TestCase(id=None, inputs={}, expected_outputs={}, metadata={}),
        runtime_states=[]
    )

    result = await evaluator.evaluate(metric, context)
    assert result.score == 0.0
    assert "Strategy execution failed: LLM call failed" in result.justification
    assert result.assertion_status == AssertionStatus.FAIL


@pytest.mark.asyncio
@patch("app.core.eval_engine.services.metric_evaluator.evaluate_answer_relevancy_rigorous")
@patch("app.core.eval_engine.services.metric_evaluator.evaluate_context_recall_rigorous")
async def test_routing_for_other_strategies(mock_recall, mock_relevancy):
    from app.core.eval_engine.models import JudgeResult, AssertionStatus
    
    mock_relevancy.return_value = JudgeResult(score=0.8, justification=["R"], evidence=None)
    mock_recall.return_value = JudgeResult(score=0.7, justification=["C"], evidence=None)

    rs_extractor = AsyncMock()
    rs_extractor.extract_variable.side_effect = lambda variable, context: "some_value"
    
    evaluator = MetricEvaluatorService(
        rs_extractor=rs_extractor,
        formula_evaluator=AsyncMock(),
        ai_judge_service=AsyncMock()
    )

    context = EvaluationContext(
        test_case=TestCase(id=None, inputs={}, expected_outputs={}, metadata={}),
        runtime_states=[]
    )

    # Test answer relevancy strategy
    metric_ar = Metric(
        name="answer_relevancy_rigorous",
        description="AR",
        type="ai-judge",
        required_inputs=["input_text", "output_text"],
        evaluation_strategy="answer_relevancy_rigorous",
    )
    result_ar = await evaluator.evaluate(metric_ar, context)
    assert result_ar.score == 0.8
    mock_relevancy.assert_called_once()

    # Test context recall strategy
    metric_cr = Metric(
        name="context_recall_rigorous",
        description="CR",
        type="ai-judge",
        required_inputs=["retrieved_context", "testcase.expected_outputs.expected_output"],
        evaluation_strategy="context_recall_rigorous",
    )
    result_cr = await evaluator.evaluate(metric_cr, context)
    assert result_cr.score == 0.7
    mock_recall.assert_called_once()

