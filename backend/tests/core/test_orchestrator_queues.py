import asyncio
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from app.core.eval_engine.services.evaluation_orchestrator import EvaluationOrchestratorService
from app.core.eval_engine.models import PipelineRunResult, AssertionStatus, BatchRunStatus


def _make_orchestrator() -> EvaluationOrchestratorService:
    return EvaluationOrchestratorService(
        batch_result_repo=MagicMock(),
        pipeline_eval_srv=MagicMock(),
        runtime_state_repo=MagicMock(),
        dataset_repo=MagicMock(),
        pipeline_repo=MagicMock(),
    )


@pytest.mark.anyio
async def test_subscribe_receives_testcase_result():
    """A queue subscribed before evaluate_testcase completes receives the result."""
    orchestrator = _make_orchestrator()
    job_id = uuid4()

    # Subscribe a queue
    q = await orchestrator.subscribe(job_id)

    # Simulate a result being published
    fake_result = MagicMock(spec=PipelineRunResult)
    await orchestrator.publish_result(job_id, fake_result)

    received = q.get_nowait()
    assert received is fake_result


@pytest.mark.anyio
async def test_publish_sentinel_on_complete_job():
    """publish_sentinel puts None into all queues for the job."""
    orchestrator = _make_orchestrator()
    job_id = uuid4()

    q1 = await orchestrator.subscribe(job_id)
    q2 = await orchestrator.subscribe(job_id)

    await orchestrator.publish_sentinel(job_id)

    assert q1.get_nowait() is None
    assert q2.get_nowait() is None


@pytest.mark.anyio
async def test_unsubscribe_removes_queue():
    """After unsubscribe, publish_result does not enqueue into removed queue."""
    orchestrator = _make_orchestrator()
    job_id = uuid4()

    q = await orchestrator.subscribe(job_id)
    await orchestrator.unsubscribe(job_id, q)

    fake_result = MagicMock(spec=PipelineRunResult)
    await orchestrator.publish_result(job_id, fake_result)

    assert q.empty()


@pytest.mark.anyio
async def test_subscriber_queues_cleanup():
    """Verify that job_id keys are cleaned up from _subscriber_queues when empty or after sentinel."""
    orchestrator = _make_orchestrator()
    job_id = uuid4()

    # 1. Test cleanup on unsubscribe (when no subscribers left)
    q1 = await orchestrator.subscribe(job_id)
    q2 = await orchestrator.subscribe(job_id)
    assert job_id in orchestrator._subscriber_queues
    assert len(orchestrator._subscriber_queues[job_id]) == 2

    await orchestrator.unsubscribe(job_id, q1)
    assert job_id in orchestrator._subscriber_queues
    assert len(orchestrator._subscriber_queues[job_id]) == 1

    await orchestrator.unsubscribe(job_id, q2)
    assert job_id not in orchestrator._subscriber_queues

    # 2. Test cleanup on publish_sentinel
    q3 = await orchestrator.subscribe(job_id)
    assert job_id in orchestrator._subscriber_queues
    await orchestrator.publish_sentinel(job_id)
    assert job_id not in orchestrator._subscriber_queues
