from typing import Annotated
from uuid import UUID, uuid4

from app.api.dependencies import (
    get_dataset_repo,
    get_evaluation_orchestrator,
    get_metric_evaluator,
    get_metric_repo,
    get_pipeline_repo,
    get_runtime_state_repo,
)
from app.api.v1.schemas.common import StatusResponse
from app.api.v1.schemas.evals import (
    CreateEvaluationRequest,
    CreateEvaluationResponse,
    SubmitTestcaseRequest,
    SubmitTestcaseResponse,
)
from app.core.eval_engine.models import (
    BatchRunResult,
    BatchSummary,
    EvaluationContext,
    MetricRunResult,
    PipelineRunResult,
    TestCase,
)
from app.core.eval_engine.ports import (
    DatasetRepository,
    MetricRepository,
    PipelineRepository,
)
from app.core.eval_engine.services.evaluation_orchestrator import (
    EvaluationOrchestratorService,
)
from app.core.eval_engine.services.metric_evaluator import MetricEvaluatorService
from app.core.exceptions import NotFoundError
from app.core.kernel.ports import RuntimeStateRepository
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder

router = APIRouter()


@router.post('/metrics/{metric_id}/run/{runtime_id}')
async def run_metric_evaluation(
    metric_id: UUID,
    runtime_id: UUID,
    metric_repo: Annotated[MetricRepository, Depends(get_metric_repo)],
    runtime_repo: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
    evaluator: Annotated[MetricEvaluatorService, Depends(get_metric_evaluator)],
    building_mode: Annotated[bool, Query()] = True,
) -> MetricRunResult:
    """Trigger a metric evaluation manually using a persisted runtime state."""
    metric = metric_repo.find_by_id(metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail=f'Metric {metric_id} not found.')

    runtime_state = runtime_repo.find_by_id(runtime_id)
    if not runtime_state:
        raise HTTPException(
            status_code=404, detail=f'Runtime state {runtime_id} not found.'
        )

    try:
        # evaluate() is async in MetricEvaluatorService
        context = EvaluationContext(
            test_case=TestCase(
                id=uuid4(),
                inputs={'text': ''},
                expected_outputs={},
                metadata={},
            ),
            runtime_states=[runtime_state],
        )
        return await evaluator.evaluate(metric, context, building_mode=building_mode)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Evaluation failed: {str(e)}',
        ) from e


@router.post('', status_code=201)
def create_evaluation(
    request: CreateEvaluationRequest,
    pipeline_repo: Annotated[PipelineRepository, Depends(get_pipeline_repo)],
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
) -> CreateEvaluationResponse:
    pipeline = pipeline_repo.find_by_id(request.pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail='Pipeline not found')

    try:
        dataset = dataset_repo.get_by_id(request.dataset_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail='Dataset not found') from e

    job_id = uuid4()
    orchestrator.create_job(
        job_id=job_id,
        pipeline_id=pipeline.id,
        dataset_id=dataset.id,
    )

    return CreateEvaluationResponse(evaluation_id=job_id)


@router.post('/{evaluation_id}/testcases/{testcase_id}/submit')
async def submit_testcase(
    evaluation_id: UUID,
    testcase_id: UUID,
    request: SubmitTestcaseRequest,
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
) -> SubmitTestcaseResponse:
    result = await orchestrator.evaluate_testcase(
        job_id=evaluation_id,
        testcase_id=testcase_id,
        runtime_ids=request.runtime_ids,
    )
    return SubmitTestcaseResponse(status='success', result=result)


@router.post('/{evaluation_id}/complete')
async def complete_evaluation(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> StatusResponse:
    await orchestrator.complete_job(evaluation_id)
    return StatusResponse(
        status='success',
        message=f'Evaluation job {evaluation_id} marked as completed.',
    )


@router.get('/{evaluation_id}')
def get_evaluation(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
) -> BatchRunResult:
    return orchestrator.get_job(evaluation_id)


@router.get('/{evaluation_id}/summary')
def get_evaluation_summary(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> BatchSummary:
    return orchestrator.get_job_summary(evaluation_id)


@router.get('/{evaluation_id}/testcases/{testcase_id}')
def get_testcase_evaluation(
    evaluation_id: UUID,
    testcase_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> PipelineRunResult:
    return orchestrator.get_testcase_result(evaluation_id, testcase_id)


@router.get('/{evaluation_id}/pipelines')
def get_evaluation_pipelines(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
) -> list[PipelineRunResult]:
    return orchestrator.get_pipeline_results(evaluation_id)


@router.get('/{evaluation_id}/pipelines/{pipeline_run_id}')
def get_pipeline_result(
    evaluation_id: UUID,
    pipeline_run_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
) -> PipelineRunResult:
    return orchestrator.get_pipeline_result(evaluation_id, pipeline_run_id)


@router.get('/{evaluation_id}/metrics/{metric_id}')
def get_metric_results(
    evaluation_id: UUID,
    metric_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> list[MetricRunResult]:
    return orchestrator.get_metric_results(evaluation_id, metric_id)


@router.get('')
def list_evaluations(
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 50,
) -> list[BatchRunResult]:
    """List all evaluation jobs with pagination."""
    return orchestrator.list_jobs(skip=skip, limit=limit)


@router.get('/{evaluation_id}/stream')
async def stream_evaluation(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
) -> StreamingResponse:
    """SSE endpoint that streams PipelineRunResult events as testcases complete."""
    from app.core.eval_engine.services.evaluation_orchestrator import EvaluationOrchestratorService as Svc

    # Verify job exists
    try:
        orchestrator.get_job(evaluation_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f'Evaluation {evaluation_id} not found.')

    async def event_generator():
        q = await Svc.subscribe(evaluation_id)
        try:
            while True:
                item = await asyncio.wait_for(q.get(), timeout=30.0)
                if item is None:
                    yield f"event: job_complete\ndata: {json.dumps({'status': 'COMPLETED'})}\n\n"
                    break
                yield f"event: testcase_complete\ndata: {json.dumps(jsonable_encoder(item))}\n\n"
        except asyncio.TimeoutError:
            # Keep-alive: no events for 30s, send a comment and loop
            yield ": keep-alive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await Svc.unsubscribe(evaluation_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
