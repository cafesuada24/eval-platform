import json
from collections.abc import Callable
from typing import Any

from app.models.telemetry import RuntimeState
from jinja2 import Template


def extract_input_text(state: RuntimeState) -> str:
    return state.input_text

def extract_output_text(state: RuntimeState) -> str:
    return state.output_text

def extract_retrieved_context(state: RuntimeState) -> Any:
    if state.events:
        for ev in state.events:
            if ev.event_type == "retrieval.completed" and "retrieved_context" in ev.payload:
                return ev.payload["retrieved_context"]
    if state.metadata and "retrieved_context" in state.metadata:
        return state.metadata["retrieved_context"]
    return None

def extract_latency_ms(state: RuntimeState) -> float | None:
    if state.events:
        for ev in state.events:
            if ev.event_type == "generation.completed" and "latency_ms" in ev.payload:
                return float(ev.payload["latency_ms"])
    if state.resource_usage and "latency_ms" in state.resource_usage:
        return float(state.resource_usage["latency_ms"])
    return None

def extract_input_artifacts_ocr(state: RuntimeState) -> Any:
    if state.events:
        for ev in state.events:
            if ev.event_type == "ocr.completed" and "input_artifacts_ocr" in ev.payload:
                return ev.payload["input_artifacts_ocr"]
    if state.metadata and "input_artifacts_ocr" in state.metadata:
        return state.metadata["input_artifacts_ocr"]
    return None

def extract_ocr_process_time_ms(state: RuntimeState) -> float | None:
    if state.events:
        for ev in state.events:
            if ev.event_type == "ocr.completed" and "ocr_process_time_ms" in ev.payload:
                return float(ev.payload["ocr_process_time_ms"])
    if state.resource_usage and "ocr_process_time_ms" in state.resource_usage:
        return float(state.resource_usage["ocr_process_time_ms"])
    return None

def extract_ocr_failed_rate(state: RuntimeState) -> float | None:
    if state.events:
        for ev in state.events:
            if ev.event_type == "ocr.completed" and "ocr_failed_rate" in ev.payload:
                return float(ev.payload["ocr_failed_rate"])
    if state.resource_usage and "ocr_failed_rate" in state.resource_usage:
        return float(state.resource_usage["ocr_failed_rate"])
    return None

def extract_retrieval_time_ms(state: RuntimeState) -> float | None:
    if state.events:
        for ev in state.events:
            if ev.event_type == "retrieval.completed" and "retrieval_time_ms" in ev.payload:
                return float(ev.payload["retrieval_time_ms"])
    if state.resource_usage and "retrieval_time_ms" in state.resource_usage:
        return float(state.resource_usage["retrieval_time_ms"])
    return None

def extract_pdf_process_time_ms(state: RuntimeState) -> float | None:
    if state.events:
        for ev in state.events:
            if ev.event_type == "pdf.completed" and "pdf_process_time_ms" in ev.payload:
                return float(ev.payload["pdf_process_time_ms"])
    if state.resource_usage and "pdf_process_time_ms" in state.resource_usage:
        return float(state.resource_usage["pdf_process_time_ms"])
    return None

def extract_pdf_failed_rate(state: RuntimeState) -> float | None:
    if state.events:
        for ev in state.events:
            if ev.event_type == "pdf.completed" and "pdf_failed_rate" in ev.payload:
                return float(ev.payload["pdf_failed_rate"])
    if state.resource_usage and "pdf_failed_rate" in state.resource_usage:
        return float(state.resource_usage["pdf_failed_rate"])
    return None

# Extractor Registry
SYSTEM_EXTRACTOR_REGISTRY: dict[str, Callable[[RuntimeState], Any]] = {
    "input_text": extract_input_text,
    "output_text": extract_output_text,
    "retrieved_context": extract_retrieved_context,
    "latency_ms": extract_latency_ms,
    "input_artifacts_ocr": extract_input_artifacts_ocr,
    "ocr_process_time_ms": extract_ocr_process_time_ms,
    "ocr_failed_rate": extract_ocr_failed_rate,
    "retrieval_time_ms": extract_retrieval_time_ms,
    "pdf_process_time_ms": extract_pdf_process_time_ms,
    "pdf_failed_rate": extract_pdf_failed_rate,
}

def serialize_for_llm(value: Any) -> str:
    """Serializes complex Python data structures into clean string representations for LLM prompts."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except Exception:
        return str(value)

def resolve_bindings(state: RuntimeState, required_inputs: list[str]) -> dict[str, str]:
    """Resolves a list of required variables using the Extractor Registry.

    Raises ValueError if a variable is not supported or if the extraction returns None.
    """
    resolved: dict[str, str] = {}
    for var_name in required_inputs:
        if var_name not in SYSTEM_EXTRACTOR_REGISTRY:
            raise ValueError(f"Required input '{var_name}' is not supported by the system extractor registry.")

        extractor = SYSTEM_EXTRACTOR_REGISTRY[var_name]
        value = extractor(state)
        if value is None:
            raise ValueError(f"Required input '{var_name}' could not be extracted from the runtime state.")

        resolved[var_name] = serialize_for_llm(value)
    return resolved

def format_prompt(template_str: str, bindings: dict[str, str]) -> str:
    """Renders a Jinja2 template with resolved variable bindings."""
    template = Template(template_str)
    return template.render(**bindings)
