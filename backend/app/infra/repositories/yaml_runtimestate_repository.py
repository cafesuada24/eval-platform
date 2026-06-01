"""YAML implementation of RuntimeStateRepository."""

from pathlib import Path
from uuid import UUID

import yaml
from app.core.exceptions import NotFoundError
from app.core.kernel.models import RuntimeState
from app.core.kernel.ports import RuntimeStateRepository
from pydantic import TypeAdapter


class YamlRuntimeStateRepository(RuntimeStateRepository):
    """YAML file-based runtime state repository."""

    def __init__(self, fixtures_dir: str | Path) -> None:
        """Initialize the repository with a directory path."""
        self.fixtures_dir = Path(fixtures_dir)
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.adapter = TypeAdapter(RuntimeState)

    def find_by_id(self, runtime_id: UUID) -> RuntimeState | None:
        """Find a runtime state by id."""
        file_path = self.fixtures_dir / f'{runtime_id}.yaml'
        if not file_path.exists():
            return None

        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    return self.adapter.validate_python(data)
        except Exception:
            pass
        return None

    def get_by_id(self, runtime_id: UUID) -> RuntimeState:
        """Get a runtime state by id."""
        state = self.find_by_id(runtime_id)
        if not state:
            raise NotFoundError(f'RuntimeState with ID {runtime_id} not found.')
        return state

    def save(self, state: RuntimeState) -> None:
        """Save a runtime state to a YAML file."""
        file_path = self.fixtures_dir / f'{state.runtime_id}.yaml'
        data = self.adapter.dump_python(state, mode='json', exclude_none=True)
        with file_path.open('w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, sort_keys=False)

    def list_all(self) -> list[RuntimeState]:
        """List all runtime states."""
        states: list[RuntimeState] = []
        for file_path in self.fixtures_dir.glob('*.yaml'):
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        states.append(self.adapter.validate_python(data))
            except Exception:
                pass
        return states

    def delete(self, runtime_id: UUID) -> None:
        """Delete a runtime state."""
        file_path = self.fixtures_dir / f'{runtime_id}.yaml'
        file_path.unlink(missing_ok=True)
