"""Runtime builders."""

from typing import Any

from app.core.kernel.models import RuntimeEvent, RuntimeState


class RuntimeStateBuilder:
    """A runtime state builder."""

    def __init__(self) -> None:
        """Initialize a builder."""
        self.__runtime = RuntimeState()

    def artifact(self, artifact: dict[str, Any]) -> None:
        """Add an artifact."""
        if self.__runtime.artifacts is None:
            self.__runtime.artifacts = []
        self.__runtime.artifacts.append(artifact)

    def event(
        self,
        event_type: str,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a runtime event."""
        self.__runtime.events.append(RuntimeEvent(
            runtime_id=self.__runtime.runtime_id,
            event_type=event_type,
            payload=payload,
            metadata=metadata,
        ))

    def metadata(self, key: str, value: Any) -> None:
        """Add metadata."""
        if self.__runtime.metadata is None:
            self.__runtime.metadata = {}
        self.__runtime.metadata[key] = value

    def latency_ms(self, latency: int) -> None:
        """Set runtime latency."""
        self.__runtime.resource_usage.latency_ms = latency

    def memory_mb(self, memory: int) -> None:
        """Set runtime cost."""
        self.__runtime.resource_usage.memory_mb = memory

    def cost_usd(self, cost: float) -> None:
        """Set runtime cost."""
        self.__runtime.resource_usage.estimated_cost_usd = cost

    def token_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Set token usage."""
        self.__runtime.resource_usage.input_tokens = input_tokens
        self.__runtime.resource_usage.output_tokens = output_tokens

    def build(self) -> RuntimeState:
        """Build the runtime state."""
        return self.__runtime
