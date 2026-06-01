"""Runtime state extractor service."""

from collections.abc import Callable

from app.core.eval_engine.models import EvaluationContext

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
    for state in context.runtime_states:
        for ev in state.events:
            if ev.event_type in ('generation.started', 'generation.start'):
                if 'input_text' in ev.payload:
                    return ev.payload['input_text']
                if 'prompt' in ev.payload:
                    return ev.payload['prompt']
    return None


@extractor('output_text')
def extract_output_text(context: EvaluationContext) -> str | None:
    for state in context.runtime_states:
        for ev in state.events:
            if ev.event_type in ('generation.completed', 'generation.end'):
                if 'output_text' in ev.payload:
                    return ev.payload['output_text']
                if 'response' in ev.payload:
                    return ev.payload['response']
    return None


@extractor('retrieved_context')
def extract_retrieved_context(context: EvaluationContext) -> str | None:
    for state in context.runtime_states:
        for ev in state.events:
            if ev.event_type != 'retrieval.completed':
                continue
            if 'retrieved_context' in ev.payload:
                return ev.payload['retrieved_context']
            if 'chunks' in ev.payload:
                # Format chunks if it's stored as a list
                chunks = ev.payload['chunks']
                if not chunks:
                    return 'No relevant documents found.'
                formatted: list[str] = []
                for i, chunk in enumerate(chunks):
                    # Handle both dict and Pydantic model cases for serialization
                    if isinstance(chunk, dict):
                        doc = chunk.get('document', {})
                        text = doc.get('text', '')
                        meta = doc.get('metadata', {})
                        doc_name = meta.get('filename', doc.get('id', 'Unknown'))
                        score = chunk.get('score', 0.0)
                    else:
                        doc = getattr(chunk, 'document', chunk)
                        text = getattr(doc, 'text', '')
                        meta = getattr(doc, 'metadata', {})
                        doc_name = meta.get('filename', getattr(doc, 'id', 'Unknown'))
                        score = getattr(chunk, 'score', 0.0)

                    formatted.append(
                        f'--- Document {i + 1} (Source: {doc_name}, Confidence Score: {score:.4f}) ---\n{text}\n'
                    )
                return '\n'.join(formatted)

        if state.metadata and 'retrieved_context' in state.metadata:
            return state.metadata['retrieved_context']
    return None


@extractor('ocr_time_ms')
def ocr_latency_ms(context: EvaluationContext) -> str | None:
    for state in context.runtime_states:
        for ev in state.events:
            if ev.event_type == 'ocr.completed' and 'latency_ms' in ev.payload:
                return ev.payload['latency_ms']
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
        """Extract a variable from runtime state."""
        extractor = EXTRACTOR_REGISTRY.get(variable)
        if extractor is None:
            raise ValueError(f'Invalid variable {variable}.')
        return extractor(context)
