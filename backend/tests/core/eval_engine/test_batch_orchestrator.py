"""Tests for batch orchestrator."""

import asyncio
from uuid import uuid4

import pytest
from app.core.eval_engine.models import (
    BatchRunResult,
    BatchRunStatus,
    Dataset,
    Pipeline,
    PipelineRunResult,
    AssertionStatus,
    TestCase,
)
from app.core.eval_engine.services.batch_orchestrator import BatchOrchestratorService


class MockBatchResultRepository:
    def __init__(self):
        self.results = {}

    def save(self, result: BatchRunResult) -> None:
        self.results[result.job_id] = result

    def get_by_id(self, job_id) -> BatchRunResult:
        return self.results[job_id]


class MockPipelineEvaluatorService:
    def __init__(self):
        self.calls = 0

    async def evaluate(self, pipeline, context):
        self.calls += 1
        return PipelineRunResult(
            evaluation_context_id=context.id,
            pipeline_id=pipeline.id,
            overall_status=AssertionStatus.PASS,
            metric_results=[],
        )


@pytest.mark.asyncio
async def test_batch_orchestrator_run_batch_async():
    repo = MockBatchResultRepository()
    evaluator = MockPipelineEvaluatorService()
    orchestrator = BatchOrchestratorService(repo, evaluator, max_concurrent_tasks=2)

    pipeline = Pipeline(name="test_pipeline", metrics=[])
    dataset = Dataset(
        id=uuid4(),
        name="test_dataset",
        cases=[
            TestCase(id=uuid4(), input_text="t1", input_files=[], expected_output=None, metadata={}),
            TestCase(id=uuid4(), input_text="t2", input_files=[], expected_output=None, metadata={}),
        ],
    )
    job_id = uuid4()

    await orchestrator.run_batch_async(pipeline, dataset, job_id)

    # Verify results
    assert job_id in repo.results
    result = repo.results[job_id]
    assert result.status == BatchRunStatus.COMPLETED
    assert len(result.pipeline_run_results) == 2
    assert evaluator.calls == 2
