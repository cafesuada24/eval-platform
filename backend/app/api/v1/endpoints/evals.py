from typing import Annotated, Any
from uuid import UUID, uuid4

from app.api.dependencies import (
    get_dataset_repo,
    get_evaluation_orchestrator,
    get_metric_evaluator,
    get_metric_repo,
    get_pipeline_repo,
    get_runtime_state_repo,
)
from app.api.v1.schemas.evals import (
    BatchSummary,
    CreateEvaluationRequest,
    CreateEvaluationResponse,
    MetricSummary,
    SubmitTestcaseRequest,
)
from app.core.eval_engine.models import (
    AssertionStatus,
    BatchRunResult,
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
from app.core.kernel.ports import RuntimeStateRepository
from fastapi import APIRouter, Depends, HTTPException, Query

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
                input_text='',
                input_files=[],
                expected_output=None,
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
    except Exception as e:
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
    pipeline_repo: Annotated[PipelineRepository, Depends(get_pipeline_repo)],
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> dict[str, Any]:
    try:
        job = orchestrator._EvaluationOrchestratorService__batch_result_repo.get_by_id(
            evaluation_id,
        )
        pipeline = pipeline_repo.get_by_id(job.pipeline_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f'Job or Pipeline not found: {str(e)}',
        ) from e

    try:
        result = await orchestrator.evaluate_testcase(
            job_id=evaluation_id,
            pipeline=pipeline,
            testcase_id=testcase_id,
            runtime_ids=request.runtime_ids,
        )
        return {'status': 'success', 'result': result}
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f'Failed to evaluate testcase: {str(e)}'
        ) from e


@router.post('/{evaluation_id}/complete')
def complete_evaluation(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> dict[str, Any]:
    try:
        orchestrator.complete_job(evaluation_id)
        return {'status': 'completed', 'evaluation_id': str(evaluation_id)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Job not found: {str(e)}') from e


@router.get('/{evaluation_id}', response_model=BatchRunResult)
def get_evaluation(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
) -> BatchRunResult:
    try:
        return orchestrator._EvaluationOrchestratorService__batch_result_repo.get_by_id(
            evaluation_id,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Job not found: {str(e)}') from e


@router.get('/{evaluation_id}/summary')
def get_evaluation_summary(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> BatchSummary:
    try:
        job = orchestrator._EvaluationOrchestratorService__batch_result_repo.get_by_id(
            evaluation_id
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Job not found: {str(e)}') from e

    metric_stats = {}

    for pr in job.pipeline_run_results:
        for mr in pr.metric_results:
            if mr.metric_id not in metric_stats:
                metric_stats[mr.metric_id] = {
                    'total_score': 0.0,
                    'pass_count': 0,
                    'fail_count': 0,
                    'warning_count': 0,
                    'total_runs': 0,
                }

            stats = metric_stats[mr.metric_id]
            stats['total_score'] += mr.score
            stats['total_runs'] += 1

            if mr.assertion_status == AssertionStatus.PASS:
                stats['pass_count'] += 1
            elif mr.assertion_status == AssertionStatus.FAIL:
                stats['fail_count'] += 1
            elif mr.assertion_status == AssertionStatus.WARNING:
                stats['warning_count'] += 1

    metric_summaries: list[MetricSummary] = []
    for m_id, stats in metric_stats.items():
        total_runs = stats['total_runs']
        average_score = stats['total_score'] / total_runs if total_runs > 0 else 0.0
        pass_rate = (stats['pass_count'] / total_runs) * 100 if total_runs > 0 else 0.0

        metric_summaries.append(
            MetricSummary(
                metric_id=m_id,
                average_score=average_score,
                pass_count=stats['pass_count'],
                fail_count=stats['fail_count'],
                warning_count=stats['warning_count'],
                pass_rate=pass_rate,
                total_runs=total_runs,
            ),
        )

    return BatchSummary(
        job_id=job.job_id,
        pipeline_id=job.pipeline_id,
        metrics=metric_summaries,
    )


@router.get(
    '/{evaluation_id}/testcases/{testcase_id}', response_model=PipelineRunResult
)
def get_testcase_evaluation(
    evaluation_id: UUID,
    testcase_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> PipelineRunResult:
    try:
        job = orchestrator._EvaluationOrchestratorService__batch_result_repo.get_by_id(
            evaluation_id
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Job not found: {str(e)}')

    result = next(
        (pr for pr in job.pipeline_run_results if pr.testcase_id == testcase_id), None
    )
    if not result:
        raise HTTPException(
            status_code=404, detail=f'Test case result not found for {testcase_id}'
        )

    return result


@router.get('/{evaluation_id}/pipelines', response_model=list[PipelineRunResult])
def get_evaluation_pipelines(
    evaluation_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> list[PipelineRunResult]:
    try:
        job = orchestrator._EvaluationOrchestratorService__batch_result_repo.get_by_id(
            evaluation_id
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Job not found: {str(e)}')

    return job.pipeline_run_results


@router.get(
    '/{evaluation_id}/pipelines/{pipeline_run_id}', response_model=PipelineRunResult
)
def get_pipeline_result(
    evaluation_id: UUID,
    pipeline_run_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> PipelineRunResult:
    try:
        job = orchestrator._EvaluationOrchestratorService__batch_result_repo.get_by_id(
            evaluation_id
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Job not found: {str(e)}')

    result = next(
        (pr for pr in job.pipeline_run_results if pr.run_id == pipeline_run_id), None
    )
    if not result:
        raise HTTPException(
            status_code=404, detail=f'Pipeline result not found for {pipeline_run_id}'
        )

    return result


@router.get(
    '/{evaluation_id}/metrics/{metric_id}', response_model=list[MetricRunResult]
)
def get_metric_results(
    evaluation_id: UUID,
    metric_id: UUID,
    orchestrator: Annotated[
        EvaluationOrchestratorService, Depends(get_evaluation_orchestrator)
    ],
) -> list[MetricRunResult]:
    try:
        job = orchestrator._EvaluationOrchestratorService__batch_result_repo.get_by_id(
            evaluation_id
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Job not found: {str(e)}')

    results = []
    for pr in job.pipeline_run_results:
        for mr in pr.metric_results:
            if mr.metric_id == metric_id:
                results.append(mr)

    return results


@router.get('', response_model=list[BatchRunResult])
def list_evaluations(
    orchestrator: Annotated[
        EvaluationOrchestratorService,
        Depends(get_evaluation_orchestrator),
    ],
) -> list[BatchRunResult]:
    """List all evaluation jobs."""
    return orchestrator.list_jobs()
