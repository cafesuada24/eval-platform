import pytest
from app.models.telemetry import RuntimeState
from app.engine.resolver import (
    serialize_for_llm,
    resolve_bindings,
    format_prompt,
    SYSTEM_EXTRACTOR_REGISTRY
)

def test_serialize_for_llm():
    assert serialize_for_llm(None) == ""
    assert serialize_for_llm("hello") == "hello"
    assert serialize_for_llm(123) == "123"
    assert serialize_for_llm(45.6) == "45.6"
    assert serialize_for_llm(True) == "True"
    assert serialize_for_llm([1, 2, 3]) == "[\n  1,\n  2,\n  3\n]"
    assert serialize_for_llm({"key": "val"}) == "{\n  \"key\": \"val\"\n}"

def test_resolve_bindings_success():
    state = RuntimeState(
        trace_id="trace-123",
        input_text="What is FastAPI?",
        output_text="FastAPI is a modern web framework.",
        resource_usage={"latency_ms": 150.5},
        artifacts=[{"type": "retrieved_context", "content": ["FastAPI docs", "FastAPI tutorial"]}],
        metadata={"user": "admin"}
    )
    
    required = ["input_text", "output_text", "latency_ms", "retrieved_context"]
    resolved = resolve_bindings(state, required)
    
    assert resolved["input_text"] == "What is FastAPI?"
    assert resolved["output_text"] == "FastAPI is a modern web framework."
    assert resolved["latency_ms"] == "150.5"
    assert "FastAPI docs" in resolved["retrieved_context"]

def test_resolve_bindings_metadata_fallback():
    # Test fallback extraction of retrieved_context and latency_ms from metadata
    state = RuntimeState(
        trace_id="trace-123",
        input_text="hello",
        output_text="world",
        metadata={
            "retrieved_context": "context from metadata",
            "latency_ms": "300"
        }
    )
    
    required = ["retrieved_context", "latency_ms"]
    resolved = resolve_bindings(state, required)
    assert resolved["retrieved_context"] == "context from metadata"
    assert resolved["latency_ms"] == "300.0"

def test_resolve_bindings_unsupported_variable():
    state = RuntimeState(trace_id="t", input_text="in", output_text="out")
    with pytest.raises(ValueError) as excinfo:
        resolve_bindings(state, ["non_existent_var"])
    assert "is not supported by the system extractor registry" in str(excinfo.value)

def test_resolve_bindings_missing_value():
    state = RuntimeState(trace_id="t", input_text="in", output_text="out")
    # latency_ms is not present in state
    with pytest.raises(ValueError) as excinfo:
        resolve_bindings(state, ["latency_ms"])
    assert "could not be extracted from the runtime state" in str(excinfo.value)

def test_format_prompt():
    template = "Prompt: {{ input_text }}\nResponse: {{ output_text }}\nContext: {{ retrieved_context }}"
    bindings = {
        "input_text": "hello",
        "output_text": "world",
        "retrieved_context": "metadata context"
    }
    rendered = format_prompt(template, bindings)
    assert rendered == "Prompt: hello\nResponse: world\nContext: metadata context"
