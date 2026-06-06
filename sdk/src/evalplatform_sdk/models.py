"""Pydantic models and tracking classes for the EvalPlatform SDK."""

import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, TypedDict

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
)

ArtifactType = Literal[
    'document/text',  # Markdown, TXT
    'document/pdf',
    'image/ocr',  # Tesseract/Vision API results
    'image/caption',  # Descriptive image alt-text
    'generated/description',  # LLM outputted image context
]
class Artifact(BaseModel):
    """A multimodal object attached to a trace."""

    model_config = ConfigDict(validate_assignment=True)

    type: ArtifactType
    content: str
    metadata: dict[str, Any] | None = None


class GenerationPayload(BaseModel):
    """Payload for generation events."""

    model_config = ConfigDict(validate_assignment=True)

    provider: str = ''
    model: str = ''

    input_text: str = ''
    prompt: str = ''
    output_text: str = ''

    latency_ms: NonNegativeInt = 0
    input_tokens: int = 0
    output_tokens: int = 0

    event_type: Literal['generation'] = 'generation'


class RetrievedChunk(TypedDict):
    """A chunk of retrieved document text."""

    document: str
    content: str
    confidence: float


class RetrievalPayload(BaseModel):
    """Payload for retrieval events."""

    model_config = ConfigDict(validate_assignment=True)

    query: str = ''
    chunks: list[RetrievedChunk] = Field(default_factory=list[RetrievedChunk])
    latency_ms: int = 0

    event_type: Literal['retrieval'] = 'retrieval'


class FileProcessedPayload(BaseModel):
    """Payload for file processing events."""

    model_config = ConfigDict(validate_assignment=True)

    file_name: str = ''
    processor: Literal['ocr', 'file_reader'] = 'file_reader'

    content: str = ''
    latency_ms: int = 0

    event_type: Literal['file_processed'] = 'file_processed'



type RuntimeEventPayload = Annotated[
    GenerationPayload | RetrievalPayload | FileProcessedPayload,
    Discriminator(discriminator='event_type'),
]


class GenerationTracker:
    """Tracker for LLM generation operations."""

    def __init__(self, state: GenerationPayload) -> None:
        """Initialize tracker with payload state."""
        self.__gen_state = state

    def model_info(self, provider: str, model_name: str) -> None:
        """Set model info."""
        self.__gen_state.provider = provider
        self.__gen_state.model = model_name

    def user_input(self, user_input: str) -> None:
        """Set user input text."""
        self.__gen_state.input_text = user_input

    def prompt(self, prompt: str) -> None:
        """Set raw prompt sent to the model."""
        self.__gen_state.prompt = prompt

    def output_text(self, output_text: str) -> None:
        """Set model output text."""
        self.__gen_state.output_text = output_text

    def latency_ms(self, latency_ms: int) -> None:
        """Set latency in milliseconds."""
        self.__gen_state.latency_ms = latency_ms

    def token_usage(self, input_tokens: int | None, output_tokens: int | None) -> None:
        """Set token usage."""
        if input_tokens is not None:
            self.__gen_state.input_tokens = input_tokens
        if output_tokens is not None:
            self.__gen_state.output_tokens = output_tokens


class RetrievalTracker:
    """Tracker for document retrieval operations."""

    def __init__(self, state: RetrievalPayload) -> None:
        """Initialize tracker with payload state."""
        self.__retrieval_state = state

    def query(self, query: str) -> None:
        """Set search query."""
        self.__retrieval_state.query = query

    def add_chunk(self, document: str, content: str, confidence: float) -> None:
        """Append retrieved chunk."""
        self.__retrieval_state.chunks.append(RetrievedChunk(document=document, content=content, confidence=confidence))

    def latency_ms(self, latency_ms: int) -> None:
        """Set latency in milliseconds."""
        self.__retrieval_state.latency_ms = latency_ms


class FileProcessedTracker:
    """Tracker for file processing operations."""

    def __init__(self, state: FileProcessedPayload) -> None:
        """Initialize tracker with payload state."""
        self.__file_state = state

    def file_info(self, file_name: str, processor: Literal['ocr', 'file_reader']) -> None:
        """Set file information."""
        self.__file_state.file_name = file_name
        self.__file_state.processor = processor

    def content(self, content: str) -> None:
        """Set parsed or extracted content."""
        self.__file_state.content = content

    def latency_ms(self, latency_ms: int) -> None:
        """Set latency in milliseconds."""
        self.__file_state.latency_ms = latency_ms


# --- ENTITIES ---


class ResourceUsage(BaseModel):
    """Total resource usage of a trace."""

    input_tokens: NonNegativeInt = 0
    output_tokens: NonNegativeInt = 0
    latency_ms: NonNegativeInt = 0
    memory_mb: NonNegativeInt = 0
    estimated_cost_usd: NonNegativeFloat = 0


class RuntimeEvent(BaseModel):
    """Runtime event.

    A specific event happened in a trace.
    """

    runtime_id: str  # The trace id
    payload: RuntimeEventPayload
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] | None = None



class RuntimeState(BaseModel):
    """Runtime state.

    Containing collected events, artifacts,
    resource usage and metadata of a chat turn.
    """

    runtime_id: str
    events: list[RuntimeEvent] = Field(default_factory=list[RuntimeEvent])
    usage: ResourceUsage = Field(default_factory=ResourceUsage)
    artifacts: list[Artifact] = Field(default_factory=list[Artifact])
    metadata: dict[str, Any] | None = None

    @property
    def input_text(self) -> str | None:
        """Helper to get the input text of the last generation event."""
        for event in reversed(self.events):
            if isinstance(event.payload, GenerationPayload):
                return event.payload.input_text
        return None

    @input_text.setter
    def input_text(self, value: str) -> None:
        """Helper to set the input text of the generation event, creating it if needed."""
        for event in reversed(self.events):
            if isinstance(event.payload, GenerationPayload):
                event.payload.input_text = value
                return
        payload = GenerationPayload(input_text=value)
        self.events.append(
            RuntimeEvent(
                runtime_id=self.runtime_id,
                payload=payload,
            ),
        )

    @property
    def output_text(self) -> str | None:
        """Helper to get the output text of the last generation event."""
        for event in reversed(self.events):
            if isinstance(event.payload, GenerationPayload):
                return event.payload.output_text
        return None

    @output_text.setter
    def output_text(self, value: str) -> None:
        """Helper to set the output text of the generation event, creating it if needed."""
        for event in reversed(self.events):
            if isinstance(event.payload, GenerationPayload):
                event.payload.output_text = value
                return
        payload = GenerationPayload(output_text=value)
        self.events.append(
            RuntimeEvent(
                runtime_id=self.runtime_id,
                payload=payload,
            ),
        )


    @contextmanager
    def track_generation(
        self,
    ) -> Generator[GenerationTracker, None, None]:
        """Tracks an LLM generation call, appending start and end events to the state."""
        start_time = time.perf_counter()

        payload = GenerationPayload()
        tracker = GenerationTracker(state=payload)

        try:
            yield tracker
        finally:
            tracker.latency_ms(int((time.perf_counter() - start_time) * 1000.0))

            self.events.append(
                RuntimeEvent(
                    runtime_id=self.runtime_id,
                    timestamp=datetime.now(UTC),
                    payload=payload,
                ),
            )

    @contextmanager
    def track_retrieval(
        self,
    ) -> Generator[RetrievalTracker, None, None]:
        """Tracks a retrieval call, appending an event to the state."""
        start_time = time.perf_counter()

        payload = RetrievalPayload()
        tracker = RetrievalTracker(state=payload)

        try:
            yield tracker
        finally:
            tracker.latency_ms(int((time.perf_counter() - start_time) * 1000.0))

            self.events.append(
                RuntimeEvent(
                    runtime_id=self.runtime_id,
                    timestamp=datetime.now(UTC),
                    payload=payload,
                ),
            )

    @contextmanager
    def track_file_processed(
        self,
    ) -> Generator[FileProcessedTracker, None, None]:
        """Tracks a file processing call, appending an event to the state."""
        start_time = time.perf_counter()

        payload = FileProcessedPayload()
        tracker = FileProcessedTracker(state=payload)

        try:
            yield tracker
        finally:
            tracker.latency_ms(int((time.perf_counter() - start_time) * 1000.0))

            self.events.append(
                RuntimeEvent(
                    runtime_id=self.runtime_id,
                    timestamp=datetime.now(UTC),
                    payload=payload,
                ),
            )
