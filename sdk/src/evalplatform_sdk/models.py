from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ArtifactType = Literal[
    "document/text",        # Markdown, TXT
    "document/pdf",
    "image/ocr",            # Tesseract/Vision API results
    "image/caption",        # Descriptive image alt-text
    "generated/description" # LLM outputted image context
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

class RuntimeState(BaseModel):
    trace_id: str
    input_text: str | None = None
    output_text: str | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    events: list[RuntimeEvent] = Field(default_factory=list)
    resource_usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] | None = None
