"""Evaluation engine's models."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID, uuid4

from app.core.kernel.models import RuntimeEvent

if TYPE_CHECKING:
    from app.core.kernel.models import RuntimeState

# --- VALUE OBJECTS ---

class BatchRunStatus(str, Enum):
    """Batch run status."""

    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

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
                'warning_below and warning_over cannot be defined together.',
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
    is_system_default: bool = False



@dataclass(slots=True)
class MetricRunResult:
    """A metric run result."""

    metric_id: UUID
    score: float
    justification: str
    evidence: str | None
    assertion_status: AssertionStatus
    improvements: str | None = None
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

    evaluation_context_id: UUID
    pipeline_id: UUID
    overall_status: AssertionStatus
    metric_results: list[MetricRunResult]
    testcase_id: UUID | None = None
    run_id: UUID = field(default_factory=uuid4)

@dataclass(slots=True)
class BatchRunResult:
    """A batch run result."""

    job_id: UUID
    pipeline_id: UUID
    dataset_id: UUID
    status: BatchRunStatus
    pipeline_run_results: list[PipelineRunResult] = field(default_factory=list[PipelineRunResult])

@dataclass(slots=True)
class TestCase:
    id: UUID
    input_text: str
    input_files: list[str]
    expected_output: str | None
    metadata: dict[str, Any]

@dataclass(slots=True)
class Dataset:
    id: UUID
    name: str
    cases: list[TestCase]

@dataclass(slots=True)
class EvaluationContext:
    test_case: TestCase
    runtime_states: list[RuntimeState]
    id: UUID = field(default_factory=uuid4)
    events_by_type: dict[str, list[RuntimeEvent]] = field(init=False, default_factory=dict[str, list[RuntimeEvent]])

    def __post_init__(self) -> None:
        events_dict: dict[str, list[RuntimeEvent]] = defaultdict(list[RuntimeEvent])
        for state in self.runtime_states:
            for event in state.events:
                events_dict[event.payload.event_type].append(event)
        self.events_by_type = dict(events_dict)

    @property
    def final_state(self) -> RuntimeState | None:
        return self.runtime_states[-1] if self.runtime_states else None


@dataclass(frozen=True, slots=True)
class JudgeResult:
    """An ai judge result."""
    score: float
    justification: list[str]
    evidence: list[str]
    improvements: list[str] | None = None
