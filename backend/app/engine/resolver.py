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
    # 1. Check metadata
    if state.metadata and "retrieved_context" in state.metadata:
        return state.metadata["retrieved_context"]
    if state.metadata and "context" in state.metadata:
        return state.metadata["context"]
    # 2. Check artifacts
    if state.artifacts:
        for art in state.artifacts:
            if art.get("type") == "retrieved_context":
                return art.get("content")
            if "retrieved_context" in art:
                return art["retrieved_context"]
            if "content" in art and art.get("name") == "retrieved_context":
                return art["content"]
    return None

def extract_latency_ms(state: RuntimeState) -> float | None:
    if state.resource_usage and "latency_ms" in state.resource_usage:
        try:
            return float(state.resource_usage["latency_ms"])
        except (ValueError, TypeError):
            pass
    if state.metadata and "latency_ms" in state.metadata:
        try:
            return float(state.metadata["latency_ms"])
        except (ValueError, TypeError):
            pass
    return None

# Extractor Registry
SYSTEM_EXTRACTOR_REGISTRY: dict[str, Callable[[RuntimeState], Any]] = {
    "input_text": extract_input_text,
    "output_text": extract_output_text,
    "retrieved_context": extract_retrieved_context,
    "latency_ms": extract_latency_ms,
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
