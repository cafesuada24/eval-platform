"""Pipeline evaluator service."""

import asyncio

from app.core.eval_engine.models import (
    AssertionStatus,
    EvaluationContext,
    Metric,
    MetricRunResult,
    MetricThreshold,
    Pipeline,
    PipelineRunResult,
)
from app.core.eval_engine.ports import MetricRepository
from app.core.eval_engine.services.metric_evaluator import MetricEvaluatorService


class PipelineEvaluatorService:
    """Pipeline evaluation service."""

    def __init__(
        self,
        metric_eval_srv: MetricEvaluatorService,
        metric_repo: MetricRepository,
    ) -> None:
        self.__metric_eval_srv = metric_eval_srv
        self.__metric_repo = metric_repo

    async def evaluate(
        self,
        pipeline: Pipeline,
        context: EvaluationContext,
    ) -> PipelineRunResult:
        """Run all metrics in a pipeline concurrently and aggregate outcomes."""
        metrics: list[tuple[Metric, MetricThreshold | None]] = []
        for metric_item in pipeline.metrics:
            metrics.append(
                (
                    self.__metric_repo.get_by_id(metric_item.metric_id),
                    metric_item.threshold,
                ),
            )

        tasks = [
            self.__metric_eval_srv.evaluate(
                metric,
                context,
                threshold,
            )
            for metric, threshold in metrics
        ]

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[MetricRunResult] = []
        for i, res in enumerate(raw_results):
            if isinstance(res, Exception):
                metric = metrics[i][0]
                results.append(
                    MetricRunResult(
                        metric_id=metric.id,
                        metric_name=metric.name,
                        score=0.0,
                        justification=f'Execution failed: {str(res)}',
                        evidence=None,
                        assertion_status=AssertionStatus.FAIL,
                    )
                )
            else:
                results.append(res)

        overall_status = max(
            (result.assertion_status for result in results),
            default=AssertionStatus.PASS,
        )

        return PipelineRunResult(
            evaluation_context_id=context.id,
            pipeline_id=pipeline.id,
            overall_status=overall_status,
            metric_results=list(results),
            testcase_id=context.test_case.id,
        )
