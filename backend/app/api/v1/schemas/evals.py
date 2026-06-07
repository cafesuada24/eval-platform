"""Eval routes DTOs."""

from uuid import UUID

from app.core.eval_engine.models import PipelineRunResult
from pydantic import BaseModel


class CreateEvaluationRequest(BaseModel):
    pipeline_id: UUID
    dataset_id: UUID

class CreateEvaluationResponse(BaseModel):
    evaluation_id: UUID

class SubmitTestcaseRequest(BaseModel):
    runtime_ids: list[UUID]


class SubmitTestcaseResponse(BaseModel):
    status: str
    result: PipelineRunResult



