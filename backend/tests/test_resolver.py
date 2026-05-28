import pytest
from app.models.telemetry import RuntimeState
from app.engine.resolver import (
    serialize_for_llm,
    resolve_bindings,
    format_prompt,
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
        metadata={"input_artifacts_ocr": "ocr text data"},
        events=[]
    )
    
    required = ["input_text", "output_text", "latency_ms", "input_artifacts_ocr"]
    resolved = resolve_bindings(state, required)
    
    assert resolved["input_text"] == "What is FastAPI?"
    assert resolved["output_text"] == "FastAPI is a modern web framework."
    assert resolved["latency_ms"] == "150.5"
    assert resolved["input_artifacts_ocr"] == "ocr text data"

def test_resolve_bindings_unsupported_variable():
    state = RuntimeState(trace_id="t", input_text="in", output_text="out")
    with pytest.raises(ValueError) as excinfo:
        resolve_bindings(state, ["non_existent_var"])
    assert "is not supported by the system extractor registry" in str(excinfo.value)

def test_resolve_bindings_missing_value():
    state = RuntimeState(trace_id="t", input_text="in", output_text="out")
    with pytest.raises(ValueError) as excinfo:
        resolve_bindings(state, ["latency_ms"])
    assert "could not be extracted from the runtime state" in str(excinfo.value)

def test_format_prompt():
    template = "Prompt: {{ input_text }}\nResponse: {{ output_text }}"
    bindings = {
        "input_text": "hello",
        "output_text": "world",
    }
    rendered = format_prompt(template, bindings)
    assert rendered == "Prompt: hello\nResponse: world"

def test_resolve_new_performance_metrics():
    state = RuntimeState(
        trace_id="t4", input_text="in", output_text="out",
        resource_usage={
            "ocr_process_time_ms": 1200.0,
            "ocr_failed_rate": 0.05,
            "retrieval_time_ms": 250.0,
            "pdf_process_time_ms": 3200.0,
            "pdf_failed_rate": 0.0
        }
    )
    
    required = [
        "ocr_process_time_ms",
        "ocr_failed_rate",
        "retrieval_time_ms",
        "pdf_process_time_ms",
        "pdf_failed_rate"
    ]
    resolved = resolve_bindings(state, required)
    
    assert resolved["ocr_process_time_ms"] == "1200.0"
    assert resolved["ocr_failed_rate"] == "0.05"
    assert resolved["retrieval_time_ms"] == "250.0"
    assert resolved["pdf_process_time_ms"] == "3200.0"
    assert resolved["pdf_failed_rate"] == "0.0"

def test_resolve_metrics_from_events():
    from app.models.telemetry import RuntimeEvent
    
    state = RuntimeState(
        trace_id="t5", input_text="in", output_text="out",
        events=[
            RuntimeEvent(
                event_id="e1", trace_id="t5", event_type="ocr.completed",
                payload={"ocr_process_time_ms": 1400.0, "ocr_failed_rate": 0.12}
            ),
            RuntimeEvent(
                event_id="e2", trace_id="t5", event_type="pdf.completed",
                payload={"pdf_process_time_ms": 2800.0, "pdf_failed_rate": 0.0}
            ),
            RuntimeEvent(
                event_id="e3", trace_id="t5", event_type="retrieval.completed",
                payload={"retrieval_time_ms": 190.0}
            )
        ]
    )
    
    required = [
        "ocr_process_time_ms",
        "ocr_failed_rate",
        "retrieval_time_ms",
        "pdf_process_time_ms",
        "pdf_failed_rate"
    ]
    resolved = resolve_bindings(state, required)
    
    assert resolved["ocr_process_time_ms"] == "1400.0"
    assert resolved["ocr_failed_rate"] == "0.12"
    assert resolved["retrieval_time_ms"] == "190.0"
    assert resolved["pdf_process_time_ms"] == "2800.0"
    assert resolved["pdf_failed_rate"] == "0.0"
