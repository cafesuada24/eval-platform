import atexit
import logging
import threading
from typing import Any

import httpx

from .models import RuntimeEvent

logger = logging.getLogger(__name__)


class EvalClient:
    """
    Non-blocking HTTP client for pushing telemetry data to EvalPlatform.
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
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.flush_interval_seconds = flush_interval_seconds
        self.max_buffer_size = max_buffer_size
        self.max_buffer_capacity = max_buffer_capacity

        self._buffer: list[RuntimeEvent] = []
        self._lock = threading.Lock()
        self._flush_event = threading.Event()
        self._stop_event = threading.Event()

        # Configured for graceful degradation - short timeout to not block connection pool.
        self._http_client = httpx.Client(
            timeout=2.0,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

        self._worker_thread = threading.Thread(
            target=self._background_loop, daemon=True
        )
        self._worker_thread.start()

        # Register cleanup hook to flush remaining items before process termination
        atexit.register(self.flush_sync)

    def log_event(self, event: RuntimeEvent) -> None:
        """Appends the event to the internal buffer and triggers flush if full."""
        with self._lock:
            if len(self._buffer) >= self.max_buffer_capacity:
                logger.warning(
                    "EvalPlatform client buffer is full (%d). Dropping event.",
                    self.max_buffer_capacity,
                )
                return

            self._buffer.append(event)
            should_flush = len(self._buffer) >= self.max_buffer_size

        if should_flush:
            self._flush_event.set()

    def _background_loop(self) -> None:
        """Background worker loop to flush buffer periodically."""
        while not self._stop_event.is_set():
            # Wait until either the flush interval passes or flush is triggered
            self._flush_event.wait(self.flush_interval_seconds)
            self._flush_event.clear()
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Safely extracts all items from the buffer and dispatches them via HTTP."""
        with self._lock:
            if not self._buffer:
                return

            # Extract batch and clear buffer
            payload_events = self._buffer[:]
            self._buffer.clear()

        payload = [event.model_dump(mode="json") for event in payload_events]

        try:
            # Wrap in try/except to ensure network failures don't crash the host
            response = self._http_client.post(
                f"{self.base_url}/v1/events", json={"events": payload}
            )
            response.raise_for_status()
        except Exception as e:
            logger.warning("Failed to flush telemetry events to EvalPlatform: %s", e)

    def flush_sync(self) -> None:
        """Synchronously flush remaining events. Useful for shutdown operations."""
        self._stop_event.set()
        self._flush_event.set()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=self.flush_interval_seconds + 1.0)
        self._flush_buffer()
        self._http_client.close()
