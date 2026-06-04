"""Eval routes DTOs."""

from uuid import UUID

from pydantic import BaseModel


class CreateEvaluationRequest(BaseModel):
    pipeline_id: UUID
    dataset_id: UUID

class CreateEvaluationResponse(BaseModel):
    evaluation_id: UUID

class SubmitTestcaseRequest(BaseModel):
    runtime_ids: list[UUID]


class MetricSummary(BaseModel):
    metric_id: UUID
    average_score: float
    pass_count: int
    fail_count: int
    warning_count: int
    pass_rate: float
    total_runs: int

class BatchSummary(BaseModel):
    job_id: UUID
    pipeline_id: UUID
    metrics: list[MetricSummary]

