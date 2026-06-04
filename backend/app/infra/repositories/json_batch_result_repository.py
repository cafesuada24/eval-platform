from pathlib import Path
from uuid import UUID

from app.core.eval_engine.models import BatchRunResult
from pydantic import TypeAdapter


class LocalJsonBatchResultRepository:
    """Local JSON implementation for BatchResultRepository."""

    def __init__(self, results_dir: str | Path) -> None:
        self.__results_dir = Path(results_dir)
        self.__results_dir.mkdir(exist_ok=True, parents=True)
        self.__ta = TypeAdapter(BatchRunResult)

    def _get_path(self, job_id: UUID) -> Path:
        return self.__results_dir / f'{job_id}.json'

    def get_by_id(self, job_id: UUID) -> BatchRunResult:
        """Get a batch run result by job_id."""
        path = self._get_path(job_id)
        if not path.exists() or not path.is_file():
            raise ValueError(f"BatchRunResult {job_id} not found.")
        raw_data = path.read_text(encoding='utf-8')
        return self.__ta.validate_json(raw_data)

    def save(self, result: BatchRunResult) -> None:
        """Save a batch run result."""
        path = self._get_path(result.job_id)
        path.write_bytes(self.__ta.dump_json(result))

    def list_all(self) -> list[BatchRunResult]:
        """List all batch run results."""
        results: list[BatchRunResult] = []
        for path in self.__results_dir.glob('*.json'):
            try:
                raw_data = path.read_text(encoding='utf-8')
                results.append(self.__ta.validate_json(raw_data))
            except Exception:
                pass
        return results
