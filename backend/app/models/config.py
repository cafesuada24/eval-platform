from pydantic import BaseModel


class ModelConfiguration(BaseModel):
    provider: str
    model: str
    # Flexible for additional provider-specific configuration
    model_config = {
        "extra": "allow",
    }

class ScoringScale(BaseModel):
    min: float
    max: float
    data_type: str

class MetricConfig(BaseModel):
    name: str
    type: str
    description: str
    model_configuration: ModelConfiguration
    required_inputs: list[str]
    prompt_template: str
    scoring_scale: ScoringScale

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
