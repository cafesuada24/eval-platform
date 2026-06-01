"""Metric helper agent models."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

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



class AgentEvent(BaseModel):
    """An event in an agent loop."""

    type: Literal[
        'user_message',
        'query_documents',
        'create_or_update_metric',
        'response',
        'query_documents_result',
    ]
    query: str | None = None
    response: str | None = None
    metric_draft: MetricDraft | None = None
    query_result: str | None = None

    @model_validator(mode='after')
    def validate_fields(self) -> 'AgentEvent':
        """Ensure appropriate fields are present based on type."""
        if self.type in ('user_message', 'query_documents'):
            if not self.query:
                raise ValueError(f'query is required for type {self.type}')
        elif self.type == 'create_or_update_metric':
            if not self.response or not self.metric_draft:
                raise ValueError(
                    'response and metric_draft are required for create_or_update_metric',
                )
        elif self.type == 'response':
            if not self.response:
                raise ValueError('response is required for type response')
        elif self.type == 'query_documents_result' and not self.query_result:
            raise ValueError(
                'query_result is required for type query_documents_result',
            )
        return self


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
    runtime_id: UUID | None = None


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
