from uuid import UUID

from app.core.agents.metric_helper.models import ChatMessage
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str | None = None
    messages: list[ChatMessage] | None = None
    metric_id: UUID | None = None
