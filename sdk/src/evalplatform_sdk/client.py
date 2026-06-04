"""Eval Platform SDK client."""

import atexit
import contextlib
import logging
import threading

import httpx

from .management import DatasetClient, PipelineClient
from .models import RuntimeState

logger = logging.getLogger(__name__)


class NullClient:
    """A no-op client returned when the SDK is uninitialized to prevent crashes."""

    def log_runtime(self, runtime: RuntimeState) -> None:
        pass

    def flush(self) -> None:
        pass

    def flush_sync(self) -> None:
        pass


_default_client = None


def get_default_client() -> 'EvalClient | NullClient':
    """Retrieves the default initialized EvalClient instance."""
    if _default_client is None:
        logger.warning(
            'EvalPlatform SDK is not initialized. Telemetry will be silently dropped.',
        )
        return NullClient()
    return _default_client


class EvalClient:
    """Non-blocking HTTP client for pushing telemetry data to EvalPlatform.

    Events are batched in memory and flushed asynchronously in a background thread.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        flush_interval_seconds: float = 3.0,
        max_buffer_size: int = 50,
        max_buffer_capacity: int = 5000,
    ) -> None:
        global _default_client
        if _default_client is None:
            _default_client = self

        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.flush_interval_seconds = flush_interval_seconds
        self.max_buffer_size = max_buffer_size
        self.max_buffer_capacity = max_buffer_capacity

        self._buffer: list[RuntimeState] = []
        self._lock = threading.Lock()
        self._flush_event = threading.Event()
        self._stop_event = threading.Event()

        # Configured for graceful degradation - short timeout to not block connection pool.
        self._http_client = httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=10),
            headers={'Authorization': f'Bearer {self.api_key}'},
        )

        # Dedicated client for management API calls
        self._management_client = httpx.Client(
            timeout=30.0,
            headers={'Authorization': f'Bearer {self.api_key}'},
        )
        self.datasets = DatasetClient(self._management_client, self.base_url)
        self.pipelines = PipelineClient(self._management_client, self.base_url)

        self._worker_thread = threading.Thread(
            target=self._background_loop, daemon=True,
        )
        self._worker_thread.start()

        # Register cleanup hook to flush remaining items before process termination
        atexit.register(self.flush_sync)

    def log_runtime(self, runtime: RuntimeState) -> None:
        """Appends the runtime to the internal buffer and triggers flush if full."""
        with self._lock:
            if len(self._buffer) >= self.max_buffer_capacity:
                logger.warning(
                    'EvalPlatform client buffer is full (%d). Dropping runtime.',
                    self.max_buffer_capacity,
                )
                return

            self._buffer.append(runtime)
            should_flush = len(self._buffer) >= self.max_buffer_size

        if should_flush:
            self._flush_event.set()

    def _background_loop(self) -> None:
        """Background worker loop to flush buffer periodically with exponential backoff."""
        consecutive_failures = 0
        base_backoff = 2.0

        while not self._stop_event.is_set():
            wait_time = self.flush_interval_seconds
            if consecutive_failures > 0:
                # Exponential backoff up to ~60 seconds
                wait_time = min(60.0, base_backoff**consecutive_failures)

            # Wait until either the flush interval passes or flush is triggered
            self._flush_event.wait(wait_time)
            self._flush_event.clear()

            success = self._flush_buffer()
            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1

    def _flush_buffer(self) -> bool:
        """Safely extracts batch from buffer and dispatches them via HTTP.

        Returns True on success or empty, False on network/5xx errors to trigger backoff.
        """
        with self._lock:
            if not self._buffer:
                return True

            # Extract batch and clear from buffer
            payload_runtimes = self._buffer[: self.max_buffer_size]
            del self._buffer[: self.max_buffer_size]

        payload = [runtime.model_dump(mode='json') for runtime in payload_runtimes]

        try:
            # Wrap in try/except to ensure network failures don't crash the host
            response = self._http_client.post(
                f'{self.base_url}/v1/runtimes',
                json=payload,
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                logger.warning(
                    'EvalPlatform backend error (%d). Re-queueing runtimes.',
                    e.response.status_code,
                )
                self._requeue_runtimes(payload_runtimes)
                return False
            # 4xx errors mean bad data, we shouldn't retry
            logger.warning('EvalPlatform rejected telemetry data: %s', e)
            return True
        except Exception as e:
            logger.warning('Failed to flush telemetry runtimes to EvalPlatform: %s', e)
            self._requeue_runtimes(payload_runtimes)
            return False

    def _requeue_runtimes(self, runtimes: list[RuntimeState]) -> None:
        """Pushes runtimes back into the front of the buffer, respecting max capacity."""
        with self._lock:
            combined = runtimes + self._buffer
            # Keep newest elements if capacity is exceeded
            self._buffer = combined[-self.max_buffer_capacity :]

    def flush(self) -> None:
        """Synchronously flush currently buffered runtimes without shutting down."""
        self._flush_buffer()

    def flush_sync(self) -> None:
        """Synchronously flush remaining runtimes. Useful for shutdown operations."""
        if self._stop_event.is_set():
            return

        self._stop_event.set()
        self._flush_event.set()

        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=self.flush_interval_seconds + 1.0)

        # Perform final flush (safe due to lock) if thread didn't drain buffer completely
        with contextlib.suppress(Exception):
            self._flush_buffer()

        with contextlib.suppress(Exception):
            self._http_client.close()

        with contextlib.suppress(Exception):
            self._management_client.close()
