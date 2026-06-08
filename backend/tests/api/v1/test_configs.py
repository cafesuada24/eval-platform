from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_metric_with_strategy():
    payload = {
        "name": "test_strategy_metric_api",
        "description": "Test",
        "type": "ai-judge",
        "required_inputs": ["input_text"],
        "scoring_scale": {"min": 0.0, "max": 1.0, "data_type": "float"},
        "model_configuration": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.1
        },
        "prompt_template": "Test prompt",
        "evaluation_strategy": "faithfulness_rigorous"
    }
    response = client.post("/v1/configs/metrics", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["evaluation_strategy"] == "faithfulness_rigorous"
