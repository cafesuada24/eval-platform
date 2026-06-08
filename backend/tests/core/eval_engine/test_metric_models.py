from app.api.v1.schemas.configs import MetricCreate
from app.core.eval_engine.models import Metric, ScoringScale

def test_metric_create_schema_with_strategy():
    data = {
        "name": "faithfulness_rigorous",
        "description": "Rigorous faithfulness metric",
        "type": "ai-judge",
        "required_inputs": ["retrieved_context", "output_text"],
        "scoring_scale": {"min": 0.0, "max": 1.0, "data_type": "float"},
        "evaluation_strategy": "faithfulness_rigorous"
    }
    obj = MetricCreate.model_validate(data)
    assert obj.evaluation_strategy == "faithfulness_rigorous"

def test_metric_dataclass_with_strategy():
    metric = Metric(
        name="test",
        description="test",
        type="ai-judge",
        required_inputs=["input_text"],
        evaluation_strategy="test_strategy"
    )
    assert metric.evaluation_strategy == "test_strategy"
