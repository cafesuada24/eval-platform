from typing import Literal

from app.models.config import ThresholdConfig

AssertionResult = Literal['pass', 'fail', 'warning']


def evaluate_threshold(
    score: float,
    threshold: ThresholdConfig | None,
) -> AssertionResult:
    """Evaluates a metric's score against optional semantic thresholds in order of severity:
    1. Critical failures (fail_over, fail_below)
    2. Warnings (warning_over, warning_below)
    Returns "pass" if no boundaries are breached.
    """

    if not threshold:
        return 'pass'

    # Evaluate rules in order of severity:
    # 1. Check fail thresholds first
    if threshold.fail_over is not None and score > threshold.fail_over:
        return 'fail'
    if threshold.fail_below is not None and score < threshold.fail_below:
        return 'fail'

    # 2. Check warning thresholds second
    if threshold.warning_over is not None and score > threshold.warning_over:
        return 'warning'
    if threshold.warning_below is not None and score < threshold.warning_below:
        return 'warning'

    return 'pass'
