from datetime import datetime, timezone
from evalplatform_sdk.models import Artifact, RuntimeEvent, RuntimeState
import pytest

def test_artifact_creation():
    artifact = Artifact(type="document/pdf", content="test")
    assert artifact.type == "document/pdf"
    assert artifact.content == "test"
    assert artifact.metadata is None

    artifact_with_metadata = Artifact(type="image/ocr", content="test", metadata={"foo": "bar"})
    assert artifact_with_metadata.metadata == {"foo": "bar"}

def test_runtime_event_creation():
    now = datetime.now(timezone.utc)
    event = RuntimeEvent(
        event_id="e1",
        trace_id="t1",
        event_type="generation.start",
        timestamp=now,
        payload={"foo": "bar"}
    )
    assert event.event_id == "e1"
    assert event.trace_id == "t1"
    assert event.event_type == "generation.start"
    assert event.timestamp == now
    assert event.payload == {"foo": "bar"}
    assert event.metadata is None

def test_runtime_state_defaults():
    state = RuntimeState(trace_id="t1")
    assert state.trace_id == "t1"
    assert state.input_text is None
    assert state.output_text is None
    assert state.artifacts == []
    assert state.events == []
    assert state.resource_usage == {}
    assert state.metadata is None
