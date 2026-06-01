"""Shared models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class RuntimeEventType(str, Enum):
    """Types of runtime events."""

    GENERATION_STARTED = 'generation.started'
    GENERATION_START = 'generation.start'
    GENERATION_COMPLETED = 'generation.completed'
    GENERATION_END = 'generation.end'
    RETRIEVAL_COMPLETED = 'retrieval.completed'
    OCR_COMPLETED = 'ocr.completed'


@dataclass(slots=True)
class ResourceUsage:
    """Total resource usage of a trace."""

    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    memory_mb: int = 0
    estimated_cost_usd: float = 0


@dataclass(slots=True)
class RuntimeEvent:
    """Runtime event.

    A specific event happened in a trace.
    """

    runtime_id: UUID  # The trace id
    event_type: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class RuntimeState:
    """Runtime state.

    Containing collected events, artifacts,
    resource usage and metadata of a chat turn.
    """

    runtime_id: UUID = field(default_factory=uuid4)
    events: list[RuntimeEvent] = field(default_factory=list[RuntimeEvent])
    resource_usage: ResourceUsage = field(default_factory=ResourceUsage)

    artifacts: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None
