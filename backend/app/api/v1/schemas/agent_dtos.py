from uuid import UUID

from app.core.agents.metric_helper.models import ChatMessage
from pydantic import BaseModel


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    metric_id: UUID | None = None


class SaveSessionRequest(BaseModel):
    """Payload to explicitly save a chat session."""

    messages: list[ChatMessage]
