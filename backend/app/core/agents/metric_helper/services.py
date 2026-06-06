import logging
import uuid

import yaml
from app.core.agents.metric_helper.models import (
    ChatMessage,
    ChatSession,
    MetricHelperResponse,
)
from app.core.agents.metric_helper.ports import (
    AgenticMetricHelper,
    ChatSessionRepository,
)
from app.core.eval_engine.models import Metric
from app.core.eval_engine.ports import MetricRepository
from pydantic import TypeAdapter

logger = logging.getLogger(__name__)


class MetricHelperAppService:
    """Application service for Metric Helper Agent interactions."""

    def __init__(
        self,
        agentic_helper: AgenticMetricHelper,
        metric_repo: MetricRepository,
        session_repo: ChatSessionRepository,
    ) -> None:
        self.__agentic_helper = agentic_helper
        self.__metric_repo = metric_repo
        self.__session_repo = session_repo

    async def chat(
        self,
        messages: list[ChatMessage],
        metric_id: uuid.UUID | None = None,
    ) -> MetricHelperResponse:
        """Handle a chat turn with the metric helper agent."""
        current_yaml = None

        if metric_id:
            metric_config = self.__metric_repo.find_by_id(metric_id)
            if metric_config:
                data = TypeAdapter(Metric).dump_python(
                    metric_config,
                    mode='json',
                    exclude_none=True,
                )
                current_yaml = yaml.dump(data, sort_keys=False)

        if not messages:
            raise ValueError('No message history provided in request.')

        session_id = metric_id if metric_id else uuid.uuid4()
        session = ChatSession(metric_id=session_id, messages=messages)

        result = await self.__agentic_helper.chat(
            session=session,
            current_metric_config=current_yaml,
        )

        if result.response_text:
            messages.append(
                ChatMessage(
                    role='model',
                    content=result.response_text,
                    runtime_id=result.runtime_id,
                )
            )

        if metric_id:
            try:
                session_data = ChatSession(metric_id=metric_id, messages=messages)
                self.__session_repo.save(session_data)
            except Exception as e:
                logger.error(f"Failed to save session for metric '{metric_id}': {e}", exc_info=True)

        return result
