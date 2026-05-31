"""YAML implementation of PipelineRepository."""

from pathlib import Path
from uuid import UUID

import yaml
from app.core.eval_engine.models import Pipeline
from app.core.exceptions import PipelineNotFoundError
from pydantic import TypeAdapter


class YamlPipelineRepository:
    """YAML file-based pipeline repository."""

    def __init__(self, fixtures_dir: str | Path) -> None:
        """Initialize the repository with a directory path."""
        self.__fixtures_dir = Path(fixtures_dir)
        self.__fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.__adapter = TypeAdapter(Pipeline)

    def find_by_id(self, pipeline_id: UUID) -> Pipeline | None:
        """Find a pipeline config by id."""
        file_path = self.__fixtures_dir / f'{pipeline_id}.yaml'
        if not file_path.exists():
            return None

        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    return self.__adapter.validate_python(data)
        except Exception:
            pass
        return None

    def get_by_id(self, pipeline_id: UUID) -> Pipeline:
        """Get a pipeline config by id. Raise PipelineNotFoundError if not found."""
        pipeline = self.find_by_id(pipeline_id)
        if not pipeline:
            raise PipelineNotFoundError(str(pipeline_id))
        return pipeline

    def find_by_name(self, name: str) -> Pipeline | None:
        """Find a pipeline config by name."""
        for file_path in self.__fixtures_dir.glob('*.yaml'):
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and data.get('name') == name:
                        return self.__adapter.validate_python(data)
            except Exception:
                pass
        return None

    def get_by_name(self, name: str) -> Pipeline:
        """Get a pipeline config by name. Raise PipelineNotFoundError if not found."""
        pipeline = self.find_by_name(name)
        if not pipeline:
            raise PipelineNotFoundError(name)
        return pipeline

    def save(self, pipeline: Pipeline) -> None:
        """Save a pipeline configuration to a YAML file."""
        file_path = self.__fixtures_dir / f'{pipeline.id}.yaml'
        # Dump using JSON mode to ensure enums and UUIDs are stringified
        data = self.__adapter.dump_python(pipeline, mode='json', exclude_none=True)
        with file_path.open('w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, sort_keys=False)
