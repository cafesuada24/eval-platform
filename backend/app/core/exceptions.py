"""Domain errors."""

class DomainError(Exception):
    """Raised when a domain error happens."""

class NotFoundError(DomainError):
    """Raised when something is not found."""

class MetricNotFoundError(NotFoundError):
    """Raised when a metric is not found."""

    def __init__(self, metric: str) -> None:
        super().__init__(
            f"Metric with name {metric} is not found."
        )

class PipelineNotFoundError(NotFoundError):
    """Raised when a pipeline is not found."""

    def __init__(self, pipeline: str) -> None:
        super().__init__(
            f"Pipeline with name {pipeline} is not found."
        )

