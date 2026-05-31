"""Kernel ports."""

from typing import Protocol
from uuid import UUID

from app.core.kernel.models import RuntimeState


class RuntimeStateRepository(Protocol):
    """Runtime state repository."""

    def find_by_id(self, runtime_id: UUID) -> RuntimeState | None:
        """Find a runtime state by ID."""
        ...

    def get_by_id(self, runtime_id: UUID) -> RuntimeState:
        """Get a runtime state by ID.

        Raises NotFoundError if not found.
        """
        ...

    def save(self, state: RuntimeState) -> None:
        """Save a runtime state."""
        ...
