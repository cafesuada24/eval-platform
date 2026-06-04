"""Evaluation orchestrator service."""

from typing import TYPE_CHECKING
from uuid import UUID

from app.core.eval_engine.models import (
    BatchRunResult,
    BatchRunStatus,
    EvaluationContext,
    Pipeline,
    PipelineRunResult,
)
from app.core.eval_engine.ports import BatchResultRepository, DatasetRepository
from app.core.eval_engine.services.pipeline_evaluator import PipelineEvaluatorService
from app.core.exceptions import NotFoundError
from app.core.kernel.ports import RuntimeStateRepository

if TYPE_CHECKING:
    from app.core.kernel.models import RuntimeState


class EvaluationOrchestratorService:
    """Evaluation orchestrator service."""

    def __init__(
        self,
        batch_result_repo: BatchResultRepository,
        pipeline_eval_srv: PipelineEvaluatorService,
        runtime_state_repo: RuntimeStateRepository,
        dataset_repo: DatasetRepository,
    ) -> None:
        self.__batch_result_repo = batch_result_repo
        self.__pipeline_eval_srv = pipeline_eval_srv
        self.__runtime_state_repo = runtime_state_repo
        self.__dataset_repo = dataset_repo

    def create_job(
        self,
        job_id: UUID,
        pipeline_id: UUID,
        dataset_id: UUID,
    ) -> BatchRunResult:
        """Create a new evaluation job."""
        job = BatchRunResult(
            job_id=job_id,
            pipeline_id=pipeline_id,
            dataset_id=dataset_id,
            status=BatchRunStatus.IN_PROGRESS,
            pipeline_run_results=[],
        )
        self.__batch_result_repo.save(job)
        return job

    async def evaluate_testcase(
        self,
        job_id: UUID,
        pipeline: Pipeline,
        testcase_id: UUID,
        runtime_ids: list[UUID],
    ) -> PipelineRunResult:
        """Evaluate a single test case using the provided runtime states."""
        job = self.__batch_result_repo.get_by_id(job_id)
        dataset = self.__dataset_repo.get_by_id(job.dataset_id)

        testcase = next((tc for tc in dataset.cases if tc.id == testcase_id), None)
        if not testcase:
            raise NotFoundError(
                f'Test case {testcase_id} not found in dataset {dataset.id}',
            )

        runtime_states: list[RuntimeState] = []
        for rid in runtime_ids:
            try:
                state = self.__runtime_state_repo.get_by_id(rid)
                runtime_states.append(state)
            except NotFoundError as e:
                # If a runtime state is missing, we might still want to proceed or raise error.
                # For now, we raise it.
                raise NotFoundError(f'Runtime state {rid} not found.') from e

        context = EvaluationContext(
            test_case=testcase,
            runtime_states=runtime_states,
        )

        result = await self.__pipeline_eval_srv.evaluate(pipeline, context)

        # Save result to job
        job.pipeline_run_results.append(result)
        self.__batch_result_repo.save(job)

        return result

    def complete_job(self, job_id: UUID) -> BatchRunResult:
        """Mark a job as completed."""
        job = self.__batch_result_repo.get_by_id(job_id)
        job.status = BatchRunStatus.COMPLETED
        self.__batch_result_repo.save(job)
        return job

    def list_jobs(self) -> list[BatchRunResult]:
        """List all evaluation jobs."""
        return self.__batch_result_repo.list_all()
