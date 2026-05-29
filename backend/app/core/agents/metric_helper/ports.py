"""Metric helper agent ports."""

from typing import Protocol

from app.core.agents.metric_helper.models import ChatSession, MetricHelperResponse


class AgenticMetricBuilder(Protocol):
    """Metric builder helper agent."""

    async def chat(
        self,
        session: ChatSession,
        current_metric_config: str | None = None,
    ) -> MetricHelperResponse:
        """Query the builder."""
        ...
