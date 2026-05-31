"""Metric helper agent ports."""

from typing import Protocol
from uuid import UUID

from app.core.agents.metric_helper.models import ChatSession, MetricHelperResponse


class AgenticMetricHelper(Protocol):
    """Metric builder helper agent."""

    async def chat(
        self,
        session: ChatSession,
        current_metric_config: str | None = None,
    ) -> MetricHelperResponse:
        """Query the builder."""
        ...

class ChatSessionRepository(Protocol):
    """Repository for chat sessions."""

    def find_by_id(self, metric_id: UUID) -> ChatSession | None:
        """Find a chat session by metric ID."""
        ...

    def save(self, session: ChatSession) -> None:
        """Save a chat session."""
        ...

    def delete(self, metric_id: UUID) -> None:
        """Delete a chat session."""
        ...
