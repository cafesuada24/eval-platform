import json
import asyncio
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_evaluation_orchestrator
from app.core.eval_engine.models import (
    PipelineRunResult, AssertionStatus, BatchRunResult, BatchRunStatus
)

client = TestClient(app)


def _make_batch_result(job_id):
    return BatchRunResult(
        job_id=job_id,
        pipeline_id=uuid4(),
        dataset_id=uuid4(),
        status=BatchRunStatus.IN_PROGRESS,
        pipeline_run_results=[],
    )


def test_stream_yields_testcase_complete_then_job_complete():
    """SSE endpoint streams testcase_complete events then closes on job_complete (sentinel)."""
    job_id = uuid4()
    fake_result = PipelineRunResult(
        evaluation_context_id=uuid4(),
        pipeline_id=uuid4(),
        overall_status=AssertionStatus.PASS,
        metric_results=[],
        testcase_id=uuid4(),
        run_id=uuid4(),
    )

    # Queue that yields one result then a sentinel
    q = asyncio.Queue()
    q.put_nowait(fake_result)
    q.put_nowait(None)  # sentinel = job complete

    mock_orchestrator = MagicMock()
    mock_orchestrator.get_job.return_value = _make_batch_result(job_id)

    app.dependency_overrides[get_evaluation_orchestrator] = lambda: mock_orchestrator

    try:
        with (
            patch(
                "app.core.eval_engine.services.evaluation_orchestrator.EvaluationOrchestratorService.subscribe",
                new_callable=AsyncMock,
                return_value=q,
            ),
            patch(
                "app.core.eval_engine.services.evaluation_orchestrator.EvaluationOrchestratorService.unsubscribe",
                new_callable=AsyncMock,
            ),
        ):
            with client.stream("GET", f"/v1/evaluations/{job_id}/stream") as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                body = response.read().decode()

            assert "testcase_complete" in body
            assert "job_complete" in body
    finally:
        app.dependency_overrides.clear()


def test_stream_returns_404_for_unknown_job():
    """SSE endpoint returns 404 if the job does not exist."""
    job_id = uuid4()

    mock_orchestrator = MagicMock()
    from app.core.exceptions import NotFoundError
    mock_orchestrator.get_job.side_effect = NotFoundError("not found")

    app.dependency_overrides[get_evaluation_orchestrator] = lambda: mock_orchestrator

    try:
        response = client.get(f"/v1/evaluations/{job_id}/stream")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
