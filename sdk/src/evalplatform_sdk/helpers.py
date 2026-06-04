import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager

from .client import get_default_client
from .management import CaseTracker
from .models import RuntimeState


@contextmanager
def trace(
    runtime_id: str | None = None,
    eval_tracker: CaseTracker | None = None,
) -> Generator[RuntimeState, None, None]:
    """Context manager to trace execution, calculate latency, and automatically log a RuntimeState on exit.

    If eval_tracker is provided, the trace will be attached to that testcase evaluation.
    """
    if runtime_id is None:
        runtime_id = str(uuid.uuid4())
        
    if eval_tracker is not None:
        eval_tracker.add_runtime(runtime_id)

    state = RuntimeState(runtime_id=runtime_id)

    start_time = time.perf_counter()

    try:
        yield state
    finally:
        latency_ms = int((time.perf_counter() - start_time) * 1000.0)
        state.usage.latency_ms = latency_ms

        client = get_default_client()
        client.log_runtime(state)
