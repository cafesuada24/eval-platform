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
        runtime_id="t1",
        event_type="generation.start",
        timestamp=now,
        payload={"foo": "bar"}
    )
    assert event.runtime_id == "t1"
    assert event.event_type == "generation.start"
    assert event.timestamp == now
    assert event.payload == {"foo": "bar"}
    assert event.metadata is None

def test_runtime_state_defaults():
    state = RuntimeState(runtime_id="t1")
    assert state.runtime_id == "t1"
    assert state.input_text is None
    assert state.output_text is None
    assert state.artifacts == []
    assert state.events == []
    assert state.resource_usage == {}
    assert state.metadata is None

def test_track_generation():
    state = RuntimeState(runtime_id="t1")
    with state.track_generation(model="gpt-4", custom_meta="foo") as gen:
        gen.input_tokens = 10
        gen.output_tokens = 20
        assert len(state.events) == 1
        start_event = state.events[0]
        assert start_event.event_type == "generation.start"
        assert start_event.metadata == {"model": "gpt-4", "custom_meta": "foo"}

    assert len(state.events) == 2
    end_event = state.events[1]
    assert end_event.event_type == "generation.end"
    assert end_event.payload["input_tokens"] == 10
    assert end_event.payload["output_tokens"] == 20
    assert "latency_ms" in end_event.payload
    assert end_event.payload["latency_ms"] >= 0
    assert end_event.metadata == {"model": "gpt-4", "custom_meta": "foo"}
