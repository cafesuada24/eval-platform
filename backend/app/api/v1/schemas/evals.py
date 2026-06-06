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



