from typing import Annotated
from uuid import UUID, uuid4

from app.api.dependencies import (
    get_metric_evaluator,
    get_metric_repo,
    get_runtime_state_repo,
)
from app.core.eval_engine.models import EvaluationContext, MetricRunResult, TestCase
from app.core.eval_engine.ports import MetricRepository
from app.core.eval_engine.services.metric_evaluator import MetricEvaluatorService
from app.core.kernel.ports import RuntimeStateRepository
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


@router.post("/metrics/{metric_id}/run/{runtime_id}", response_model=MetricRunResult)
async def run_metric_evaluation(
    metric_id: UUID,
    runtime_id: UUID,
    metric_repo: Annotated[MetricRepository, Depends(get_metric_repo)],
    runtime_repo: Annotated[RuntimeStateRepository, Depends(get_runtime_state_repo)],
    evaluator: Annotated[MetricEvaluatorService, Depends(get_metric_evaluator)]
) -> MetricRunResult:
    """Trigger a metric evaluation manually using a persisted runtime state."""
    metric = metric_repo.find_by_id(metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail=f"Metric {metric_id} not found.")

    runtime_state = runtime_repo.find_by_id(runtime_id)
    if not runtime_state:
        raise HTTPException(status_code=404, detail=f"Runtime state {runtime_id} not found.")

    try:
        # evaluate() is async in MetricEvaluatorService
        context = EvaluationContext(
            test_case=TestCase(
                id=uuid4(),
                input_text="",
                input_files=[],
                expected_output=None,
                metadata={},
            ),
            runtime_states=[runtime_state],
        )
        return await evaluator.evaluate(metric, context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}") from e
