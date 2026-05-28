from unittest.mock import patch, MagicMock
import pytest
from app.models.telemetry import RuntimeState
from app.models.config import PipelineConfig, PipelineMetric, ThresholdConfig
from app.engine.orchestrator import (
    load_metric_config,
    load_pipeline_config,
    _run_single_metric,
    execute_pipeline
)
from app.engine.executor import JudgeOutput

def test_load_metric_config():
    config = load_metric_config("hallucination_ai_judge")
    assert config.name == "hallucination_ai_judge"
    assert config.type == "ai-judge"
    assert "output_text" in config.required_inputs

def test_load_pipeline_config():
    config = load_pipeline_config("customer_support_rag_eval")
    assert config.name == "customer_support_rag_eval"
    assert len(config.metrics) == 1
    assert config.metrics[0].metric_name == "hallucination_ai_judge"

@pytest.mark.anyio
@patch("app.engine.orchestrator.execute_ai_judge_async")
async def test_run_single_metric(mock_execute_async):
    mock_execute_async.return_value = JudgeOutput(score=4.0, justification="Good grounding.")

    state = RuntimeState(
        trace_id="trace-123",
        input_text="Hi",
        output_text="FastAPI is modern.",
        metadata={"retrieved_context": "FastAPI modern framework"}
    )

    metric_item = PipelineMetric(
        metric_name="hallucination_ai_judge",
        threshold=ThresholdConfig(fail_over=3.5, warning_over=2.0)
    )

    result = await _run_single_metric(state, metric_item)
    assert result.metric_name == "hallucination_ai_judge"
    assert result.score == 4.0
    assert result.assertion_status == "fail"  # score 4.0 is > fail_over 3.5

@pytest.mark.anyio
@patch("app.engine.orchestrator.execute_ai_judge_async")
async def test_execute_pipeline_aggregation(mock_execute_async):
    state = RuntimeState(
        trace_id="trace-123",
        input_text="Hi",
        output_text="FastAPI is modern.",
        metadata={"retrieved_context": "FastAPI modern framework"}
    )

    # Define a pipeline with multiple metrics
    pipeline = PipelineConfig(
        name="test_pipeline",
        metrics=[
            PipelineMetric(
                metric_name="hallucination_ai_judge",
                threshold=ThresholdConfig(fail_over=4.5, warning_over=3.0)
            ),
            PipelineMetric(
                metric_name="hallucination_ai_judge",  # Re-use same for simplicity
                threshold=ThresholdConfig(fail_over=2.0)
            )
        ]
    )

    # First metric: score 3.5 -> warning (> 3.0 warning_over but <= 4.5 fail_over)
    # Second metric: score 1.5 -> pass (<= 2.0 fail_over)
    # Overall should be warning
    mock_execute_async.side_effect = [
        JudgeOutput(score=3.5, justification="Medium grounding."),
        JudgeOutput(score=1.5, justification="Perfect grounding.")
    ]

    result = await execute_pipeline(state, pipeline)
    assert result.overall_status == "warning"
    assert len(result.metric_results) == 2
    assert result.metric_results[0].assertion_status == "warning"
    assert result.metric_results[1].assertion_status == "pass"

    # Reset mock and test fail status
    # First metric: score 5.0 -> fail
    # Second metric: score 1.5 -> pass
    # Overall should be fail
    mock_execute_async.reset_mock()
    mock_execute_async.side_effect = [
        JudgeOutput(score=5.0, justification="Hallucinated completely."),
        JudgeOutput(score=1.5, justification="Perfect grounding.")
    ]

    result = await execute_pipeline(state, pipeline)
    assert result.overall_status == "fail"

def test_load_latency_seconds_config():
    config = load_metric_config("latency_seconds")
    assert config.name == "latency_seconds"
    assert config.type == "primitive"
    assert config.formula == "latency_ms / 1000"

@pytest.mark.anyio
async def test_run_single_primitive_metric_success():
    state = RuntimeState(
        trace_id="trace-123",
        input_text="Hi",
        output_text="FastAPI is modern.",
        resource_usage={"latency_ms": 1500.0}
    )

    metric_item = PipelineMetric(
        metric_name="latency_seconds",
        threshold=ThresholdConfig(fail_over=2.0, warning_over=1.0)
    )

    # 1500.0 / 1000.0 = 1.5 -> warning status (> 1.0 but <= 2.0)
    result = await _run_single_metric(state, metric_item)
    assert result.metric_name == "latency_seconds"
    assert result.score == 1.5
    assert "divided by 1000.0" in result.justification
    assert result.assertion_status == "warning"

@pytest.mark.anyio
async def test_run_single_primitive_metric_missing_target():
    state = RuntimeState(
        trace_id="trace-123",
        input_text="Hi",
        output_text="FastAPI is modern.",
        resource_usage={} # missing latency_ms
    )

    metric_item = PipelineMetric(
        metric_name="latency_seconds"
    )

    with pytest.raises(ValueError) as excinfo:
        await _run_single_metric(state, metric_item)
    assert "could not be extracted from the runtime state" in str(excinfo.value)

@pytest.mark.anyio
async def test_run_single_primitive_metric_math_operations():
    state = RuntimeState(
        trace_id="trace-123",
        input_text="Hi",
        output_text="FastAPI is modern.",
        resource_usage={"latency_ms": 100.0}
    )

    # 1. Multiply test (100.0 * 5.0 = 500.0)
    metric_config = load_metric_config("latency_seconds")
    metric_config.formula = "latency_ms * 5"

    with patch("app.engine.orchestrator.load_metric_config", return_value=metric_config):
        metric_item = PipelineMetric(metric_name="latency_seconds")
        result = await _run_single_metric(state, metric_item)
        assert result.score == 500.0
        assert "multiplied by 5.0" in result.justification

    # 2. Add test (100.0 + 10.0 = 110.0)
    metric_config.formula = "latency_ms + 10"
    with patch("app.engine.orchestrator.load_metric_config", return_value=metric_config):
        result = await _run_single_metric(state, metric_item)
        assert result.score == 110.0
        assert "added 10.0" in result.justification

    # 3. Subtract test (100.0 - 20.0 = 80.0)
    metric_config.formula = "latency_ms - 20"
    with patch("app.engine.orchestrator.load_metric_config", return_value=metric_config):
        result = await _run_single_metric(state, metric_item)
        assert result.score == 80.0
        assert "subtracted 20.0" in result.justification


