"""Runtime state extractor service."""

from collections.abc import Callable

from app.core.kernel.models import RuntimeState

type Formula = str
type Numeric = int | float
type VarBindings = dict[str, Numeric]

# Extractors

type VariableExtractedValue = str | int | float

EXTRACTOR_REGISTRY: dict[
    str,
    Callable[[RuntimeState], VariableExtractedValue | None],
] = {}


def extractor(
    variable: str,
) -> Callable[
    [Callable[[RuntimeState], VariableExtractedValue | None]],
    Callable[[RuntimeState], VariableExtractedValue | None],
]:
    """Extractor decorator."""

    def __decorator(
        fun: Callable[[RuntimeState], VariableExtractedValue | None],
    ) -> Callable[[RuntimeState], VariableExtractedValue | None]:
        EXTRACTOR_REGISTRY[variable] = fun
        return fun

    return __decorator


@extractor('input_text')
def extract_input_text(state: RuntimeState) -> str | None:
    for ev in state.events:
        if ev.event_type == 'generation.started' and 'input_text' in ev.payload:
            return ev.payload['input_text']
    return None


@extractor('output_text')
def extract_output_text(state: RuntimeState) -> str | None:
    for ev in state.events:
        if ev.event_type == 'generation.completed' and 'output_text' in ev.payload:
            return ev.payload['output_text']
    return None


@extractor('retrieved_context')
def extract_retrieved_context(state: RuntimeState) -> str | None:
    for ev in state.events:
        if ev.event_type == 'retrieval.completed' and 'retrieved_context' in ev.payload:
            return ev.payload['retrieved_context']
    if state.metadata and 'retrieved_context' in state.metadata:
        return state.metadata['retrieved_context']
    return None


@extractor('ocr_time_ms')
def ocr_latency_ms(state: RuntimeState) -> str | None:

    for ev in state.events:
        if ev.event_type == 'ocr.completed' and 'latency_ms' in ev.payload:
            return ev.payload['latency_ms']
    return None


@extractor('latency_ms')
def extract_latency_ms(state: RuntimeState) -> int | None:
    return state.resource_usage.latency_ms


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
        runtime_state: RuntimeState,
    ) -> VariableExtractedValue | None:
        """Extract a variable from runtime state."""
        extractor = EXTRACTOR_REGISTRY.get(variable)
        if extractor is None:
            raise ValueError(f'Invalid variable {variable}.')
        return extractor(runtime_state)
