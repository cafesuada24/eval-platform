"""Evaluation engine's models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Literal
from uuid import UUID, uuid4

# --- VALUE OBJECTS ---


class AssertionStatus(IntEnum):
    """Assertion status."""

    PASS = 0
    WARNING = 1
    FAIL = 2


@dataclass(slots=True, frozen=True)
class ScoringScale:
    """Scoring scale."""

    min: float
    max: float
    data_type: Literal['float', 'integer']

    def __post_init__(self) -> None:
        """Validation."""
        if self.min >= self.max:
            raise ValueError('`min` threshold must be smaller than `max` threshold.')


@dataclass(slots=True, frozen=True)
class MetricThreshold:
    """A metric threshold."""

    fail_over: float | None = None
    fail_below: float | None = None
    warning_over: float | None = None
    warning_below: float | None = None

    def __post_init__(self) -> None:
        """Validation."""
        if self.fail_below and self.fail_over:
            raise ValueError('fail_below and fail_over cannot be defined together.')
        if self.warning_below and self.warning_over:
            raise ValueError(
                'warning_below and warning_over cannot be defined together.'
            )


@dataclass(slots=True, frozen=True)
class PipelineMetric:
    """A metric configuration in a pipeline."""

    metric_id: UUID
    threshold: MetricThreshold | None = None


@dataclass(slots=True, frozen=True)
class ModelConfiguration:
    """A model configuration."""

    provider: str
    model: str
    temperature: float = 0.0

    def __post_init__(self) -> None:
        """Validation."""
        if self.temperature < 0.0 or self.temperature > 2.0:
            raise ValueError('model `temperature` must be between [0, 2]')


# --- ENTITIES ---


@dataclass(slots=True)
class Metric:
    """A metric configuration."""

    name: str
    description: str
    type: Literal['ai-judge', 'primitive']
    required_inputs: list[str]
    scoring_scale: ScoringScale = ScoringScale(0, 1, 'float')

    # ai-judge only
    model_configuration: ModelConfiguration | None = None
    prompt_template: str | None = None

    # primitive only
    formula: str | None = None

    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class MetricRunResult:
    """A metric run result."""

    metric_id: UUID
    score: float
    justification: str
    assertion_status: AssertionStatus
    run_id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class Pipeline:
    """A evaluation pipeline."""

    name: str
    metrics: list[PipelineMetric]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class PipelineRunResult:
    """A pipeline run result."""

    runtime_id: UUID
    pipeline_id: UUID
    overall_status: AssertionStatus
    metric_results: list[MetricRunResult]
    run_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class JudgeResult:
    """An ai judge result."""
    metric_id: UUID
    score: float
    justification: str
