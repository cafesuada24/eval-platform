from typing import Literal

from pydantic import BaseModel


class MetricRunResult(BaseModel):
    metric_name: str
    score: float
    justification: str
    assertion_status: Literal["pass", "fail", "warning"]

class PipelineResult(BaseModel):
    trace_id: str
    pipeline_name: str
    overall_status: Literal["pass", "fail", "warning"]
    metric_results: list[MetricRunResult]
