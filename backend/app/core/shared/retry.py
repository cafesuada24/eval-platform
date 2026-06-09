"""Async exponential-backoff retry decorator.

Usage::

    @with_retry()
    async def my_func(...) -> str:
        ...

    # Or with custom settings:
    @with_retry(max_attempts=5, base_delay=2.0, max_delay=60.0)
    async def my_func(...) -> str:
        ...
"""

import asyncio
import functools
import logging
import random
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

import litellm
from google.genai import errors as genai_errors

logger = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')

# Concrete exception types that represent transient, retryable failures.
#
# litellm hierarchy (all inherit openai.APIError via litellm wrappers):
#   - RateLimitError       → 429
#   - ServiceUnavailableError → 503
#   - BadGatewayError      → 502
#   - InternalServerError  → 500
#   - APIConnectionError   → network-level (parent of Timeout)
#
# google-genai hierarchy:
#   - ServerError          → any 5xx from the Gemini API
#   - (ClientError is 4xx — permanent, never retry)
#
# Built-ins:
#   - TimeoutError         → stdlib async/OS timeouts
#   - ConnectionError      → stdlib connection-level failures
RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    litellm.RateLimitError,
    litellm.ServiceUnavailableError,
    litellm.BadGatewayError,
    litellm.InternalServerError,
    litellm.APIConnectionError,  # also catches litellm.Timeout (subclass)
    litellm.BadRequestError,      # catches mapped quota/request errors
    genai_errors.ServerError,
    TimeoutError,
    ConnectionError,
)


def with_retry(
    max_attempts: int = 5,
    base_delay: float = 1.2,
    max_delay: float = 30.0,
    exceptions: tuple[type[BaseException], ...] = RETRYABLE_EXCEPTIONS,
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """Decorator factory for async exponential-backoff retries with full jitter.

    Args:
        max_attempts: Total number of tries (including the first attempt).
        base_delay:   Seconds for the first backoff window.
        max_delay:    Upper cap for any computed delay (seconds).
        exceptions:   Tuple of exception types to retry on.  Defaults to
                      :data:`RETRYABLE_EXCEPTIONS` covering transient litellm
                      and google-genai failures.
    """

    def decorator(
        fn: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exc: BaseException | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except BaseException as exc:
                    if not isinstance(exc, exceptions) or attempt == max_attempts:
                        raise

                    last_exc = exc
                    # Full-jitter backoff: sleep = random(0, min(cap, base * 2^(attempt-1)))
                    window = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    delay = random.uniform(0, window)
                    logger.warning(
                        '%s failed on attempt %d/%d (%s: %s). Retrying in %.2fs.',
                        fn.__qualname__,
                        attempt,
                        max_attempts,
                        type(exc).__name__,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)

            # Unreachable — satisfies type-checker (all paths raise or return).
            raise RuntimeError('Retry loop exited without result.') from last_exc

        return wrapper

    return decorator
