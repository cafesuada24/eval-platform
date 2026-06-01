"""Pipeline evaluator service."""

from app.core.eval_engine.models import MetricRunResult, Pipeline, PipelineRunResult, EvaluationContext
from app.core.eval_engine.services.metric_evaluator import MetricEvaluatorService


class PipelineEvaluatorService:
    """Pipeline evaluation service."""

    def __init__(self, metric_eval_srv: MetricEvaluatorService) -> None:
        self.__metric_eval_srv = metric_eval_srv

    async def evaluate(
        self,
        pipeline: Pipeline,
        context: EvaluationContext,
    ) -> PipelineRunResult:
        """Run all metrics in a pipeline concurrently and aggregate outcomes."""
        tasks = [
            self.__metric_eval_srv.evaluate(
                metric_item.metric,
                context,
                metric_item.threshold,
            )
            for metric_item in pipeline.metrics
        ]

        # Running sequentially to avoid over-engineering in MVP
        # TODO: replace this with strategy pattern:)
        results: list[MetricRunResult] = [await task for task in tasks]

        # TODO: replace this with strategy pattern:)
        overall_status = max(result.assertion_status for result in results)

        return PipelineRunResult(
            evaluation_context_id=context.id,
            pipeline_id=pipeline.id,
            overall_status=overall_status,
            metric_results=list(results),
        )
