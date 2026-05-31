"""Metric helper agent models."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# --- VALUE OBJECTS ---


@dataclass(slots=True, frozen=True)
class MetricDraft:
    """A metric draft."""

    name: str
    description: str
    prompt_template: str
    required_inputs: list[str]
    scoring_scale_min: float
    scoring_scale_max: float
    scoring_scale_type: Literal['integer', 'float']
    model_name: str
    model_provider: str
    model_temperature: float


# Agent intents


@dataclass(slots=True, frozen=True)
class UserMessageEvent:
    """A user query."""

    query: str


@dataclass(slots=True, frozen=True)
class CreateOrUpdateMetricEvent:
    """Creating or updating existing metric as user requested."""

    response: str
    metric_draft: MetricDraft


@dataclass(slots=True, frozen=True)
class QueryDocumentsEvent:
    """Agent need to query documents."""

    query: str

@dataclass(slots=True, frozen=True)
class QueryDocumentsResultEvent:
    """Result of a querying document event."""
    query_result: str


@dataclass(slots=True)
class AgentEvent:
    """An event in an agent loop."""

    type: Literal[
        'user_message',
        'query_documents',
        'create_or_update_metric',
        'response',
        'query_documents_result',
    ]
    data: UserMessageEvent | QueryDocumentsEvent | CreateOrUpdateMetricEvent | str | QueryDocumentsResultEvent


@dataclass(slots=True)
class Thread:
    """All events happened within an agent inference loop."""

    events: list[AgentEvent]


# --- ENTITIES ---


@dataclass(slots=True)
class ChatMessage:
    """A chat message."""

    role: Literal['model', 'user', 'tool']
    content: str


@dataclass(slots=True)
class ChatSession:
    """A chat session."""

    metric_id: UUID
    messages: list[ChatMessage]


class MetricHelperResponse(BaseModel):
    """A metric builder response."""

    response_text: str = Field(description='A friendly response.')
    metric_draft: MetricDraft | None = Field(
        default=None,
        description='The complete structured metric draft, if a metric is being created or updated. Return None if no metric is under discussion or if no changes were made.',
    )
    runtime_id: UUID
