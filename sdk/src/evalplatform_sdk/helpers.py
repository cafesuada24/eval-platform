"""Context managers and decorators for tracing and telemetry capture."""

import asyncio
import functools
import inspect
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from .client import get_default_client
from .management import CaseTracker, current_evaluation_runtimes
from .models import RuntimeState


@contextmanager
def trace(
    runtime_id: str | None = None,
    eval_tracker: CaseTracker | None = None,
) -> Generator[RuntimeState, None, None]:
    """Context manager to trace execution, calculate latency, and automatically log a RuntimeState on exit.

    If eval_tracker is provided (or if there is an active evaluation running in the context),
    the trace will be automatically attached to that testcase evaluation.
    """
    if runtime_id is None:
        runtime_id = str(uuid.uuid4())
        
    if eval_tracker is not None:
        eval_tracker.add_runtime(runtime_id)
    else:
        runtimes = current_evaluation_runtimes.get()
        if runtimes is not None:
            runtimes.append(runtime_id)

    state = RuntimeState(runtime_id=runtime_id)

    start_time = time.perf_counter()

    try:
        yield state
    finally:
        latency_ms = int((time.perf_counter() - start_time) * 1000.0)
        state.usage.latency_ms = latency_ms

        client = get_default_client()
        client.log_runtime(state)


def capture_trace(func):
    """Decorator to trace function execution, automatically logging a RuntimeState on exit.

    Supports standard synchronous functions, asynchronous functions, synchronous generators,
    and asynchronous generators.
    """
    sig = inspect.signature(func)
    is_async = asyncio.iscoroutinefunction(func)

    def _setup_trace(args, kwargs):
        kwargs_copy = dict(kwargs)
        runtime_id = kwargs_copy.pop('runtime_id', None)
        eval_tracker = kwargs_copy.pop('eval_tracker', None)

        try:
            bound = sig.bind(*args, **kwargs_copy)
        except TypeError:
            try:
                bound = sig.bind(*args, **kwargs)
                runtime_id = bound.arguments.get('runtime_id', runtime_id)
                eval_tracker = bound.arguments.get('eval_tracker', eval_tracker)
            except TypeError:
                bound = sig.bind(*args, **kwargs_copy)

        bound.apply_defaults()

        if runtime_id is None:
            runtime_id = str(uuid.uuid4())

        input_text = ""
        metadata = {}
        for k, v in bound.arguments.items():
            if k in ('runtime_id', 'eval_tracker'):
                continue
            if k in ('input_text', 'query'):
                input_text = str(v)
            else:
                metadata[k] = v

        final_args = bound.args
        final_kwargs = bound.kwargs

        return runtime_id, eval_tracker, input_text, metadata, final_args, final_kwargs

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        runtime_id, eval_tracker, input_text, metadata, final_args, final_kwargs = _setup_trace(args, kwargs)

        if eval_tracker is not None:
            eval_tracker.add_runtime(runtime_id)
        else:
            runtimes = current_evaluation_runtimes.get()
            if runtimes is not None:
                runtimes.append(runtime_id)

        start_time = time.perf_counter()
        try:
            result = await func(*final_args, **final_kwargs)
            return result
        finally:
            latency_ms = int((time.perf_counter() - start_time) * 1000.0)
            state = RuntimeState(runtime_id=runtime_id, metadata=metadata)
            state.usage.latency_ms = latency_ms
            state.input_text = input_text
            
            if 'result' in locals():
                if isinstance(result, str):
                    state.output_text = result
                elif isinstance(result, dict):
                    state.output_text = str(result)
                    state.metadata['output'] = result
                else:
                    state.output_text = str(result)

            client = get_default_client()
            client.log_runtime(state)

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        runtime_id, eval_tracker, input_text, metadata, final_args, final_kwargs = _setup_trace(args, kwargs)

        if eval_tracker is not None:
            eval_tracker.add_runtime(runtime_id)
        else:
            runtimes = current_evaluation_runtimes.get()
            if runtimes is not None:
                runtimes.append(runtime_id)

        start_time = time.perf_counter()

        if inspect.isgeneratorfunction(func):
            def generator_wrapper():
                accumulated = []
                try:
                    for chunk in func(*final_args, **final_kwargs):
                        yield chunk
                        if isinstance(chunk, str):
                            accumulated.append(chunk)
                        elif isinstance(chunk, dict):
                            accumulated.append(str(chunk))
                finally:
                    latency_ms = int((time.perf_counter() - start_time) * 1000.0)
                    state = RuntimeState(runtime_id=runtime_id, metadata=metadata)
                    state.usage.latency_ms = latency_ms
                    state.input_text = input_text
                    state.output_text = "".join(accumulated)

                    client = get_default_client()
                    client.log_runtime(state)
            return generator_wrapper()

        try:
            result = func(*final_args, **final_kwargs)
            return result
        finally:
            latency_ms = int((time.perf_counter() - start_time) * 1000.0)
            state = RuntimeState(runtime_id=runtime_id, metadata=metadata)
            state.usage.latency_ms = latency_ms
            state.input_text = input_text
            
            if 'result' in locals():
                if isinstance(result, str):
                    state.output_text = result
                elif isinstance(result, dict):
                    state.output_text = str(result)
                    state.metadata['output'] = result
                else:
                    state.output_text = str(result)

            client = get_default_client()
            client.log_runtime(state)

    if inspect.isasyncgenfunction(func):
        @functools.wraps(func)
        async def async_generator_wrapper(*args, **kwargs):
            runtime_id, eval_tracker, input_text, metadata, final_args, final_kwargs = _setup_trace(args, kwargs)

            if eval_tracker is not None:
                eval_tracker.add_runtime(runtime_id)
            else:
                runtimes = current_evaluation_runtimes.get()
                if runtimes is not None:
                    runtimes.append(runtime_id)

            start_time = time.perf_counter()
            accumulated = []
            try:
                async for chunk in func(*final_args, **final_kwargs):
                    yield chunk
                    if isinstance(chunk, str):
                        accumulated.append(chunk)
                    elif isinstance(chunk, dict):
                        accumulated.append(str(chunk))
            finally:
                latency_ms = int((time.perf_counter() - start_time) * 1000.0)
                state = RuntimeState(runtime_id=runtime_id, metadata=metadata)
                state.usage.latency_ms = latency_ms
                state.input_text = input_text
                state.output_text = "".join(accumulated)

                client = get_default_client()
                client.log_runtime(state)
        return async_generator_wrapper

    return async_wrapper if is_async else sync_wrapper
