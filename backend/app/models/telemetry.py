from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeEvent(BaseModel):
    event_id: str
    trace_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]
    metadata: dict[str, Any] | None = None

class RuntimeState(BaseModel):
    trace_id: str
    input_text: str
    output_text: str
    resource_usage: dict[str, Any] | None = None
    artifacts: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None
