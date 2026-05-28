from app.models.config import ThresholdConfig
from app.engine.asserter import evaluate_threshold

def test_evaluate_threshold_none():
    assert evaluate_threshold(3.0, None) == "pass"

def test_evaluate_threshold_pass():
    threshold = ThresholdConfig(
        fail_over=4.5,
        fail_below=1.5,
        warning_over=3.5,
        warning_below=2.0
    )
    assert evaluate_threshold(3.0, threshold) == "pass"

def test_evaluate_threshold_fail_over():
    threshold = ThresholdConfig(fail_over=4.0)
    assert evaluate_threshold(4.1, threshold) == "fail"
    assert evaluate_threshold(4.0, threshold) == "pass"

def test_evaluate_threshold_fail_below():
    threshold = ThresholdConfig(fail_below=2.0)
    assert evaluate_threshold(1.9, threshold) == "fail"
    assert evaluate_threshold(2.0, threshold) == "pass"

def test_evaluate_threshold_warning_over():
    threshold = ThresholdConfig(fail_over=4.5, warning_over=3.5)
    assert evaluate_threshold(4.6, threshold) == "fail"
    assert evaluate_threshold(3.6, threshold) == "warning"
    assert evaluate_threshold(3.5, threshold) == "pass"

def test_evaluate_threshold_warning_below():
    threshold = ThresholdConfig(fail_below=1.5, warning_below=2.5)
    assert evaluate_threshold(1.4, threshold) == "fail"
    assert evaluate_threshold(2.4, threshold) == "warning"
    assert evaluate_threshold(2.5, threshold) == "pass"
