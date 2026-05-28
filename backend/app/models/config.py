from pydantic import BaseModel, NonNegativeFloat


class ModelConfiguration(BaseModel):
    provider: str
    model: str
    temperature: NonNegativeFloat
    # Flexible for additional provider-specific configuration
    model_config = {
        'extra': 'allow',
    }


class ScoringScale(BaseModel):
    min: float
    max: float
    data_type: str


class MetricConfig(BaseModel):
    name: str
    type: str  # e.g., "ai-judge" or "primitive"
    description: str
    model_configuration: ModelConfiguration | None = None
    required_inputs: list[str]
    prompt_template: str | None = None
    scoring_scale: ScoringScale
    formula: str | None = None


class ThresholdConfig(BaseModel):
    fail_over: float | None = None
    fail_below: float | None = None
    warning_over: float | None = None
    warning_below: float | None = None


class PipelineMetric(BaseModel):
    metric_name: str
    threshold: ThresholdConfig | None = None


class PipelineConfig(BaseModel):
    name: str
    metrics: list[PipelineMetric]
