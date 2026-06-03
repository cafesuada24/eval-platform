import functools
import inspect
import time
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from .client import get_default_client
from .models import RuntimeEvent, RuntimeState


@contextmanager
def trace(trace_id: str | None = None) -> Generator[RuntimeState, None, None]:
    """Context manager to trace execution, calculate latency, and automatically log a terminal RuntimeEvent on exit."""
    trace_id = trace_id or str(uuid.uuid4())
    state = RuntimeState(trace_id=trace_id)

    start_time = time.perf_counter()
    start_timestamp = datetime.now(UTC)

    try:
        yield state
    finally:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        state.resource_usage['latency_ms'] = latency_ms

        event = RuntimeEvent(
            event_id=str(uuid.uuid4()),
            trace_id=trace_id,
            event_type='trace.completed',
            timestamp=start_timestamp,
            payload=state.model_dump(mode='json'),
        )

        client = get_default_client()
        client.log_event(event)


def capture_trace(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to wrap an AI generation function. Automatically captures
    kwargs, times the execution, captures the output, and sends it to the client.
    """
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            trace_id = kwargs.pop('trace_id', str(uuid.uuid4()))
            with trace(trace_id=trace_id) as state:
                _populate_state_inputs(state, kwargs)
                result = await func(*args, **kwargs)
                _populate_state_outputs(state, result)
                return result

        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        trace_id = kwargs.pop('trace_id', str(uuid.uuid4()))
        with trace(trace_id=trace_id) as state:
            _populate_state_inputs(state, kwargs)
            result = func(*args, **kwargs)
            _populate_state_outputs(state, result)
            return result

    return sync_wrapper


def _populate_state_inputs(state: RuntimeState, kwargs: dict[str, Any]) -> None:
    if 'input_text' in kwargs:
        state.input_text = kwargs['input_text']

    metadata = {}
    for k, v in kwargs.items():
        if k != 'input_text':
            metadata[k] = v

    if metadata:
        state.metadata = state.metadata or {}
        state.metadata.update(metadata)


def _populate_state_outputs(state: RuntimeState, result: Any) -> None:
    if isinstance(result, str):
        state.output_text = result
    else:
        state.metadata = state.metadata or {}
        state.metadata['output'] = str(result)
