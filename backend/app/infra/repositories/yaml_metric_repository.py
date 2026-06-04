"""YAML implementation of MetricRepository."""

from pathlib import Path
from uuid import UUID

import yaml
from app.core.eval_engine.models import Metric
from app.core.exceptions import MetricNotFoundError
from pydantic import TypeAdapter


class YamlMetricRepository:
    """YAML file-based metric repository."""

    def __init__(self, fixtures_dir: str | Path) -> None:
        """Initialize the repository with a directory path."""
        self.fixtures_dir = Path(fixtures_dir)
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.adapter = TypeAdapter(Metric)

    def find_by_id(self, metric_id: UUID) -> Metric | None:
        """Find a metric config by id."""
        file_path = self.fixtures_dir / f'{metric_id}.yaml'
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

    def get_by_id(self, metric_id: UUID) -> Metric:
        """Get a metric config by id."""
        metric = self.find_by_id(metric_id)
        if not metric:
            raise MetricNotFoundError(str(metric_id))
        return metric

    def find_by_name(self, name: str) -> Metric | None:
        """Find a metric config by name."""
        for file_path in self.fixtures_dir.glob('*.yaml'):
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and data.get('name') == name:
                        return self.adapter.validate_python(data)
            except Exception:
                # In a real implementation, we might want to log parsing errors
                pass
        return None

    def get_by_name(self, name: str) -> Metric:
        """Get a metric config by name. Raise MetricNotFoundError if not found."""
        metric = self.find_by_name(name)
        if not metric:
            raise MetricNotFoundError(name)
        return metric

    def list_all(self) -> list[Metric]:
        """List all metric configurations."""
        metrics: list[Metric] = []
        for file_path in self.fixtures_dir.glob('*.yaml'):
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        metrics.append(self.adapter.validate_python(data))
            except Exception:
                pass
        return metrics

    def save(self, metric: Metric) -> None:
        """Save a metric configuration to a YAML file."""
        file_path = self.fixtures_dir / f'{metric.id}.yaml'
        # Dump using JSON mode to ensure enums and UUIDs are stringified
        data = self.adapter.dump_python(metric, mode='json', exclude_none=True)
        with file_path.open('w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, sort_keys=False)

    def delete(self, metric_id: UUID) -> None:
        """Delete a metric configuration YAML file."""
        file_path = self.fixtures_dir / f'{metric_id}.yaml'
        if file_path.exists():
            file_path.unlink()
