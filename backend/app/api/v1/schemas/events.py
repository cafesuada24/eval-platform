"""Event DTOs."""

from uuid import UUID

from app.core.kernel.models import RuntimeEventPayload
from pydantic import AwareDatetime, BaseModel


class EventInputRequest(BaseModel):
    runtime_id: UUID
    payload: RuntimeEventPayload
    timestamp: AwareDatetime

class EventInputResponse(BaseModel):
    event_id: UUID

class EventGetResponse(EventInputRequest):
    event_id: UUID



