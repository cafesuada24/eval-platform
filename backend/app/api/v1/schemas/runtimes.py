"""Runtime DTOs."""

from typing import Any
from uuid import UUID

from app.api.v1.schemas.events import EventGetResponse, EventInputRequest
from app.core.kernel.models import ResourceUsage
from pydantic import BaseModel


class RuntimeIngestionRequest(BaseModel):
    events: list[EventInputRequest]
    usage: ResourceUsage
    runtime_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class RuntimeIngestionResponse(BaseModel):
    runtime_id: UUID

class RuntimeStateGetResponse(BaseModel):
    runtime_id: UUID
    usage: ResourceUsage
    events: list[EventGetResponse]
    metadata: dict[str, Any] | None


