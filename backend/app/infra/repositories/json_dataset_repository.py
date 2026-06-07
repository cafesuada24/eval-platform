from pathlib import Path
from uuid import UUID

from app.core.eval_engine.models import Dataset
from app.core.exceptions import NotFoundError
from pydantic import TypeAdapter, ValidationError


class LocalJsonDatasetRepository:
    """Local JSON implementation for DatasetRepository."""

    def __init__(self, datasets_dir: str | Path) -> None:
        self.__datasets_dir = Path(datasets_dir)
        self.__datasets_dir.mkdir(exist_ok=True, parents=True)
        self.__ta = TypeAdapter(Dataset)

    def _get_path(self, dataset_id: UUID) -> Path:
        return self.__datasets_dir / f'{dataset_id}.json'

    def get_by_id(self, dataset_id: UUID) -> Dataset:
        """Get a dataset by id."""
        path = self._get_path(dataset_id)
        if not path.exists() or not path.is_file():
            raise NotFoundError(f"Dataset {dataset_id} not found.")
        raw_data = path.read_text(encoding='utf-8')
        return self.__ta.validate_json(raw_data)

    def save(self, dataset: Dataset) -> None:
        """Save a dataset."""
        path = self._get_path(dataset.id)
        path.write_bytes(self.__ta.dump_json(dataset))

    def list_all(self) -> list[Dataset]:
        """List all datasets."""
        datasets: list[Dataset] = []
        for path in self.__datasets_dir.glob('*.json'):
            if not path.is_file():
                continue
            try:
                raw_data = path.read_text(encoding='utf-8')
                datasets.append(self.__ta.validate_json(raw_data))
            except ValidationError:
                continue
        return datasets
