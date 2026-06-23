"""Retry utilities for Gemini API and other network operations."""

import functools
import logging
import random
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar
from google.genai import errors as genai_errors

logger = logging.getLogger(__name__)

T = TypeVar('T')
P = ParamSpec('P')

def is_retryable_exception(exc: BaseException) -> bool:
    """Checks if the exception is transient and can be retried.

    Retryable exceptions include:
    - ConnectionError and TimeoutError (standard library)
    - ServerError (from google-genai, which covers 5xx)
    - APIError (from google-genai) with status code 429 or 5xx
    """
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True

    if isinstance(exc, genai_errors.ServerError):
        return True

    if isinstance(exc, genai_errors.APIError):
        try:
            code = int(exc.code) if exc.code is not None else None
        except (ValueError, TypeError):
            code = None
        if code in (429, 500, 502, 503, 504):
            return True

    return False

def retry_api_call(
    func: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    use_jitter: bool = True,
) -> T:
    """Executes a function with exponential backoff and optional jitter on transient errors."""
    delay = initial_delay
    for attempt in range(1, max_retries + 2):
        try:
            return func()
        except BaseException as e:
            if not is_retryable_exception(e) or attempt == max_retries + 1:
                if attempt == max_retries + 1:
                    logger.error(
                        "API call failed after %d attempts: %s",
                        max_retries + 1,
                        e,
                    )
                  # In test scenarios, mock function's side effects are raised here.
                raise

            backoff_limit = min(max_delay, delay)
            sleep_time = (
                random.uniform(0, backoff_limit) if use_jitter else backoff_limit
            )

            logger.warning(
                "API call failed (attempt %d/%d) with %s: %s. Retrying in %.2fs...",
                attempt,
                max_retries + 1,
                type(e).__name__,
                e,
                sleep_time,
            )
            time.sleep(sleep_time)
            delay *= 2.0
    raise RuntimeError("Unreachable")

def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    use_jitter: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to apply retry logic to a function on transient errors."""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return retry_api_call(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                use_jitter=use_jitter,
            )
        return wrapper
    return decorator
