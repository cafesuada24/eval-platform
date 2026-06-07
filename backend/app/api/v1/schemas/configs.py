from typing import Literal

from app.core.eval_engine.models import (
    ModelConfiguration,
    PipelineMetric,
    ScoringScale,
)
from pydantic import BaseModel


class MetricCreate(BaseModel):
    name: str
    description: str
    type: Literal['ai-judge', 'primitive']
    required_inputs: list[str]
    scoring_scale: ScoringScale
    model_configuration: ModelConfiguration | None = None
    prompt_template: str | None = None
    formula: str | None = None


class PipelineCreate(BaseModel):
    name: str
    metrics: list[PipelineMetric]
