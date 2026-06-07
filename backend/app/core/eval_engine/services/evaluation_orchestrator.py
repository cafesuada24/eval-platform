"""Evaluation orchestrator service."""

import asyncio
from typing import TYPE_CHECKING, TypedDict
from uuid import UUID

from app.core.eval_engine.models import (
    AssertionStatus,
    BatchRunResult,
    BatchRunStatus,
    BatchSummary,
    EvaluationContext,
    MetricRunResult,
    MetricSummary,
    Pipeline,
    PipelineRunResult,
)
from app.core.eval_engine.ports import BatchResultRepository, DatasetRepository, PipelineRepository
from app.core.eval_engine.services.pipeline_evaluator import PipelineEvaluatorService
from app.core.exceptions import NotFoundError
from app.core.kernel.ports import RuntimeStateRepository

if TYPE_CHECKING:
    from app.core.kernel.models import RuntimeState


class _MetricAccumulator(TypedDict):
    name: str
    total_score: float
    pass_count: int
    fail_count: int
    warning_count: int
    total_runs: int


class EvaluationOrchestratorService:
    """Evaluation orchestrator service."""

    # TODO: These locks are stored in-memory and are process-bound.
    # If the backend is scaled horizontally (multi-instance/process architecture) in the future,
    # we should upgrade to:
    # 1. Distributed locking via Redis or a database-level lock (e.g., SELECT FOR UPDATE).
    # 2. Or refactor the batch results repository to write test case results as separate files
    #    (e.g., in a directory `results/{job_id}/{testcase_id}.json`) to completely avoid write contention.
    _locks: dict[UUID, asyncio.Lock] = {}
    _global_lock = asyncio.Lock()

    @classmethod
    async def _get_lock(cls, job_id: UUID) -> asyncio.Lock:
        async with cls._global_lock:
            if job_id not in cls._locks:
                cls._locks[job_id] = asyncio.Lock()
            return cls._locks[job_id]

    def __init__(
        self,
        batch_result_repo: BatchResultRepository,
        pipeline_eval_srv: PipelineEvaluatorService,
        runtime_state_repo: RuntimeStateRepository,
        dataset_repo: DatasetRepository,
        pipeline_repo: PipelineRepository,
    ) -> None:
        self.__batch_result_repo = batch_result_repo
        self.__pipeline_eval_srv = pipeline_eval_srv
        self.__runtime_state_repo = runtime_state_repo
        self.__dataset_repo = dataset_repo
        self.__pipeline_repo = pipeline_repo

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
        testcase_id: UUID,
        runtime_ids: list[UUID],
    ) -> PipelineRunResult:
        """Evaluate a single test case using the provided runtime states."""
        job = self.get_job(job_id)
        
        try:
            pipeline = self.__pipeline_repo.get_by_id(job.pipeline_id)
        except Exception as e:
            raise NotFoundError(f'Pipeline {job.pipeline_id} not found') from e

        try:
            dataset = self.__dataset_repo.get_by_id(job.dataset_id)
        except Exception as e:
            raise NotFoundError(f'Dataset {job.dataset_id} not found') from e

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

        # Save result to job using a lock to avoid concurrent overwrite race conditions
        lock = await self._get_lock(job_id)
        async with lock:
            # Re-read the job to make sure we append to the most up-to-date pipeline_run_results
            job = self.get_job(job_id)
            job.pipeline_run_results.append(result)
            self.__batch_result_repo.save(job)

        return result

    async def complete_job(self, job_id: UUID) -> BatchRunResult:
        """Mark a job as completed."""
        lock = await self._get_lock(job_id)
        async with lock:
            job = self.get_job(job_id)
            job.status = BatchRunStatus.COMPLETED
            self.__batch_result_repo.save(job)
            return job

    def list_jobs(self, skip: int = 0, limit: int = 50) -> list[BatchRunResult]:
        """List all evaluation jobs."""
        jobs = self.__batch_result_repo.list_all()
        return jobs[skip : skip + limit]

    def get_job(self, job_id: UUID) -> BatchRunResult:
        """Get a single job by id."""
        try:
            return self.__batch_result_repo.get_by_id(job_id)
        except Exception as e:
            raise NotFoundError(f'Job {job_id} not found') from e

    def get_job_summary(self, job_id: UUID) -> BatchSummary:
        """Get the evaluation job summary."""
        job = self.get_job(job_id)
        metric_stats: dict[UUID, _MetricAccumulator] = {}

        for pr in job.pipeline_run_results:
            for mr in pr.metric_results:
                if mr.metric_id not in metric_stats:
                    metric_stats[mr.metric_id] = {
                        'name': mr.metric_name,
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

        metric_summaries = []
        for m_id, stats in metric_stats.items():
            total_runs = stats['total_runs']
            average_score = stats['total_score'] / total_runs if total_runs > 0 else 0.0
            pass_rate = (stats['pass_count'] / total_runs) * 100 if total_runs > 0 else 0.0

            metric_summaries.append(
                MetricSummary(
                    metric_id=m_id,
                    metric_name=stats['name'],
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

    def get_testcase_result(self, job_id: UUID, testcase_id: UUID) -> PipelineRunResult:
        """Get a test case result by id."""
        job = self.get_job(job_id)
        result = next(
            (pr for pr in job.pipeline_run_results if pr.testcase_id == testcase_id), None
        )
        if not result:
            raise NotFoundError(f'Test case result not found for {testcase_id}')
        return result

    def get_pipeline_results(self, job_id: UUID) -> list[PipelineRunResult]:
        """Get all pipeline results for a job."""
        job = self.get_job(job_id)
        return job.pipeline_run_results

    def get_pipeline_result(self, job_id: UUID, pipeline_run_id: UUID) -> PipelineRunResult:
        """Get a specific pipeline result for a job."""
        job = self.get_job(job_id)
        result = next(
            (pr for pr in job.pipeline_run_results if pr.run_id == pipeline_run_id), None
        )
        if not result:
            raise NotFoundError(f'Pipeline result not found for {pipeline_run_id}')
        return result

    def get_metric_results(self, job_id: UUID, metric_id: UUID) -> list[MetricRunResult]:
        """Get all metric results for a job by metric id."""
        job = self.get_job(job_id)
        results = []
        for pr in job.pipeline_run_results:
            for mr in pr.metric_results:
                if mr.metric_id == metric_id:
                    results.append(mr)
        return results
