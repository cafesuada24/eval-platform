import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ArtifactType = Literal[
    'document/text',  # Markdown, TXT
    'document/pdf',
    'image/ocr',  # Tesseract/Vision API results
    'image/caption',  # Descriptive image alt-text
    'generated/description',  # LLM outputted image context
]


class Artifact(BaseModel):
    type: ArtifactType
    content: Any
    metadata: dict[str, Any] | None = None


class RuntimeEvent(BaseModel):
    event_id: str
    trace_id: str
    event_type: str
    timestamp: datetime
    payload: dict[str, Any]
    metadata: dict[str, Any] | None = None


class GenerationTracker:
    def __init__(self) -> None:
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.latency_ms: float = 0.0


class RuntimeState(BaseModel):
    trace_id: str
    input_text: str | None = None
    output_text: str | None = None
    artifacts: list[Artifact] = Field(default_factory=list[Artifact])
    events: list[RuntimeEvent] = Field(default_factory=list[RuntimeEvent])
    resource_usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] | None = None

    @contextmanager
    def track_generation(
        self, model: str | None = None, **metadata: Any,
    ) -> Generator[GenerationTracker, None, None]:
        """Tracks an LLM generation call, appending start and end events to the state."""
        event_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        meta = metadata.copy()
        if model:
            meta['model'] = model

        self.events.append(
            RuntimeEvent(
                event_id=event_id,
                trace_id=self.trace_id,
                event_type='generation.start',
                timestamp=datetime.now(UTC),
                payload={},
                metadata=meta,
            ),
        )

        tracker = GenerationTracker()

        try:
            yield tracker
        finally:
            tracker.latency_ms = (time.perf_counter() - start_time) * 1000.0

            payload = {
                'input_tokens': tracker.input_tokens,
                'output_tokens': tracker.output_tokens,
                'latency_ms': tracker.latency_ms,
            }

            self.events.append(
                RuntimeEvent(
                    event_id=str(uuid.uuid4()),
                    trace_id=self.trace_id,
                    event_type='generation.end',
                    timestamp=datetime.now(UTC),
                    payload=payload,
                    metadata=meta,
                ),
            )
