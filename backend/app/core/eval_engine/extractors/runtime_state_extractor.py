"""Runtime state extractor service."""

import logging
from collections.abc import Callable

from app.core.eval_engine.models import EvaluationContext
from app.core.kernel.models import (
    FileProcessedPayload,
    RetrievalPayload,
    RuntimeEvent,
    RuntimeEventType,
)

logger = logging.getLogger(__name__)


type Formula = str
type Numeric = int | float
type VarBindings = dict[str, Numeric]

# Extractors

type VariableExtractedValue = str | int | float

EXTRACTOR_REGISTRY: dict[
    str,
    Callable[[EvaluationContext], VariableExtractedValue | None],
] = {}


def extractor(
    variable: str,
) -> Callable[
    [Callable[[EvaluationContext], VariableExtractedValue | None]],
    Callable[[EvaluationContext], VariableExtractedValue | None],
]:
    """Extractor decorator."""

    def __decorator(
        fun: Callable[[EvaluationContext], VariableExtractedValue | None],
    ) -> Callable[[EvaluationContext], VariableExtractedValue | None]:
        EXTRACTOR_REGISTRY[variable] = fun
        return fun

    return __decorator


@extractor('input_text')
def extract_input_text(context: EvaluationContext) -> str | None:
    events: list[RuntimeEvent] = []
    events.extend(context.events_by_type.get(RuntimeEventType.GENERATION, []))
    if not events:
        return None
    return events[-1].payload.input_text


@extractor('output_text')
def extract_output_text(context: EvaluationContext) -> str | None:
    events: list[RuntimeEvent] = []
    events.extend(context.events_by_type.get(RuntimeEventType.GENERATION, []))
    if not events:
        return None
    return events[-1].payload.output_text


@extractor('retrieved_context')
def extract_retrieved_context(context: EvaluationContext) -> str | None:
    events = context.events_by_type.get(RuntimeEventType.RETRIEVAL, [])

    formatted: list[str] = []
    chunk_index = 1
    has_retrieval_events = False

    for ev in events:
        if not isinstance(ev.payload, RetrievalPayload):
            logging.warning(
                "Retrieved non retrieval payload during 'retrieved_context' extraction"
            )
            continue

        has_retrieval_events = True
        chunks = ev.payload.chunks
        if not chunks:
            continue

        for chunk in chunks:
            doc = chunk['document']
            text = chunk['content']
            score = chunk['confidence']
            formatted.append(
                f'--- Document {chunk_index} (Source: {doc}, Confidence Score: {score:.4f}) ---\n{text}\n'
            )
            chunk_index += 1

    if has_retrieval_events:
        if not formatted:
            return 'No relevant documents found.'
        return '\n'.join(formatted)

    for state in context.runtime_states:
        if state.metadata and 'retrieved_context' in state.metadata:
            return state.metadata['retrieved_context']
    return None


@extractor('ocr_latency_ms')
def ocr_latency_ms(context: EvaluationContext) -> int | None:
    events = context.events_by_type.get(RuntimeEventType.FILE_PROCESSED, [])
    if not events:
        return None
    for ev in events:
        if (
            isinstance(ev.payload, FileProcessedPayload)
            and ev.payload.processor == 'ocr'
        ):
            return ev.payload.latency_ms
    return None


@extractor('latency_ms')
def extract_latency_ms(context: EvaluationContext) -> int | None:
    total = 0
    found = False
    for state in context.runtime_states:
        if state.resource_usage and state.resource_usage.latency_ms:
            total += state.resource_usage.latency_ms
            found = True
    return total if found else None


# ==========
class RuntimeStateExtractorService:
    """Runtime state extractor."""

    @staticmethod
    def get_supported_runtime_variables() -> list[str]:
        """Return a list of supported runtime variables."""
        return list(EXTRACTOR_REGISTRY.keys())

    @staticmethod
    def extract_variable(
        variable: str,
        context: EvaluationContext,
    ) -> VariableExtractedValue | None:
        """Extract a variable from runtime state or test case."""
        # Dynamic extraction from testcase body (e.g. testcase.inputs.image_url)
        if variable.startswith('testcase.'):
            parts = variable.split('.', 2)
            if len(parts) == 3:
                domain = parts[1]
                key = parts[2]
                if domain == 'inputs':
                    return context.test_case.inputs.get(key)
                if domain == 'expected_outputs':
                    return context.test_case.expected_outputs.get(key)
                if domain == 'metadata':
                    return context.test_case.metadata.get(key)
            raise ValueError(
                f"Invalid testcase variable format '{variable}'. Expected format: testcase.<inputs|expected_outputs|metadata>.<key>"
            )

        extractor = EXTRACTOR_REGISTRY.get(variable)
        if extractor is None:
            raise ValueError(f'Invalid variable {variable}.')
        return extractor(context)
