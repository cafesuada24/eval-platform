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
    from evalplatform_sdk.models import GenerationPayload
    now = datetime.now(timezone.utc)
    payload = GenerationPayload(
        provider="google",
        model="gemini-1.5-flash",
        input_text="hello",
        output_text="world",
    )
    event = RuntimeEvent(
        runtime_id="t1",
        timestamp=now,
        payload=payload
    )
    assert event.runtime_id == "t1"
    assert event.payload.event_type == "generation"
    assert event.payload.provider == "google"
    assert event.payload.model == "gemini-1.5-flash"
    assert event.timestamp == now
    assert event.metadata is None

def test_runtime_state_defaults():
    state = RuntimeState(runtime_id="t1")
    assert state.runtime_id == "t1"
    assert state.input_text is None
    assert state.output_text is None
    assert state.artifacts == []
    assert state.events == []
    assert state.usage.latency_ms == 0
    assert state.metadata is None

def test_track_generation():
    state = RuntimeState(runtime_id="t1")
    with state.track_generation() as gen:
        gen.model_info(provider="google", model_name="gemini-1.5-flash")
        gen.user_input("hello")
        gen.output_text("world")
        gen.token_usage(input_tokens=10, output_tokens=20)

    assert len(state.events) == 1
    event = state.events[0]
    assert event.payload.event_type == "generation"
    assert event.payload.provider == "google"
    assert event.payload.model == "gemini-1.5-flash"
    assert event.payload.input_text == "hello"
    assert event.payload.output_text == "world"
    assert event.payload.input_tokens == 10
    assert event.payload.output_tokens == 20
    assert event.payload.latency_ms >= 0

