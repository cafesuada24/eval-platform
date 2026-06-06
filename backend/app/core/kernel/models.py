"""Shared models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, TypedDict
from uuid import UUID, uuid4

from pydantic import Discriminator

# --- VALUE OBJECTS ---

class RuntimeEventType(StrEnum):
    GENERATION = 'generation'
    RETRIEVAL = 'retrieval'
    FILE_PROCESSED = 'file_processed'


@dataclass(slots=True, frozen=True)
class GenerationPayload:
    provider: str
    model: str

    input_text: str
    prompt: str
    output_text: str

    latency_ms: int
    input_tokens: int
    output_tokens: int

    event_type: Literal[RuntimeEventType.GENERATION] = RuntimeEventType.GENERATION


class RetrievedChunk(TypedDict):
    document: str
    content: str
    confidence: float


@dataclass(slots=True, frozen=True)
class RetrievalPayload:
    query: str
    chunks: list[RetrievedChunk]
    latency_ms: int

    event_type: Literal[RuntimeEventType.RETRIEVAL] = RuntimeEventType.RETRIEVAL


@dataclass(slots=True, frozen=True)
class FileProcessedPayload:
    file_name: str
    processor: Literal['ocr', 'file_reader']

    content: str
    latency_ms: int

    event_type: Literal[RuntimeEventType.FILE_PROCESSED] = RuntimeEventType.FILE_PROCESSED


type RuntimeEventPayload = Annotated[
    GenerationPayload | RetrievalPayload | FileProcessedPayload,
    Discriminator(discriminator='event_type'),
]


# --- ENTITIES ---


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
    payload: RuntimeEventPayload
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] | None = None
    event_id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class RuntimeState:
    """Runtime state.

    Containing collected events, artifacts,
    resource usage and metadata of a chat turn.
    """

    runtime_id: UUID = field(default_factory=uuid4)
    events: list[RuntimeEvent] = field(default_factory=list)
    resource_usage: ResourceUsage = field(default_factory=ResourceUsage)

    # artifacts: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None
