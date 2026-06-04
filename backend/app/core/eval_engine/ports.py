"""Evaluation engine ports."""

from typing import Protocol
from uuid import UUID

from app.core.eval_engine.models import (
    BatchRunResult,
    Dataset,
    JudgeResult,
    Metric,
    Pipeline,
)


class MetricRepository(Protocol):
    """Metric repository."""

    def find_by_name(self, name: str) -> Metric | None:
        """Find a metric config by name."""
        ...

    def get_by_name(self, name: str) -> Metric:
        """Get a metric config by name.

        Raise MetricNotFoundError if not found.
        """
        ...

    def find_by_id(self, metric_id: UUID) -> Metric | None:
        """Find a metric config by id."""
        ...

    def get_by_id(self, metric_id: UUID) -> Metric:
        """Get a metric config by id.

        Raise MetricNotFoundError if not found.
        """
        ...

    def list_all(self) -> list[Metric]:
        """List all metric configurations."""
        ...

    def save(self, metric: Metric) -> None:
        """Save a metric configuration."""
        ...

    def delete(self, metric_id: UUID) -> None:
        """Delete a metric configuration."""
        ...


class PipelineRepository(Protocol):
    """Pipeline repository."""

    def find_by_id(self, pipeline_id: UUID) -> Pipeline | None:
        """Find a metric by id."""
        ...

    def get_by_id(self, pipeline_id: UUID) -> Pipeline:
        """Find a metric by id."""
        ...

    def find_by_name(self, name: str) -> Pipeline | None:
        """Find a metric config by name."""
        ...

    def get_by_name(self, name: str) -> Pipeline:
        """Get a metric config by name.

        Raise PipelineNotFoundError if not found.
        """
        ...

    def list_all(self) -> list[Pipeline]:
        """List all pipeline configurations."""
        ...

    def save(self, pipeline: Pipeline) -> None:
        """Save a pipeline configuration."""
        ...


class AIJudgeService(Protocol):
    """AI as a judge."""

    async def evaluate(self, metric: Metric, prompt: str, building_mode: bool = False) -> JudgeResult:
        """Evaluate a metric based on a runtime state."""
        ...

class DatasetRepository(Protocol):
    """Dataset repository."""

    def get_by_id(self, dataset_id: UUID) -> Dataset:
        """Get a dataset by id."""
        ...

    def save(self, dataset: Dataset) -> None:
        """Save a dataset."""
        ...

    def list_all(self) -> list[Dataset]:
        """List all datasets."""
        ...


class BatchResultRepository(Protocol):
    """Batch result repository."""

    def get_by_id(self, job_id: UUID) -> BatchRunResult:
        """Get a batch run result by job_id."""
        ...

    def save(self, result: BatchRunResult) -> None:
        """Save a batch run result."""
        ...

    def list_all(self) -> list[BatchRunResult]:
        """List all batch run results."""
        ...

