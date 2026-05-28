from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ingest_events():
    event_payload = [
        {
            "event_id": "event-123",
            "trace_id": "trace-456",
            "event_type": "generation.start",
            "timestamp": "2026-05-28T10:00:00Z",
            "payload": {"prompt": "Hello world"},
            "metadata": {"user_id": "user-789"}
        },
        {
            "event_id": "event-124",
            "trace_id": "trace-456",
            "event_type": "generation.end",
            "timestamp": "2026-05-28T10:00:02Z",
            "payload": {"response": "Hello!"},
            "metadata": {"user_id": "user-789"}
        }
    ]
    
    response = client.post("/v1/events", json=event_payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "Processing batch of 2 events" in data["message"]

def test_ingest_events_invalid_payload():
    # Payload missing event_type
    invalid_payload = [
        {
            "event_id": "event-123",
            "trace_id": "trace-456",
            "timestamp": "2026-05-28T10:00:00Z",
            "payload": {"prompt": "Hello world"}
        }
    ]
    
    response = client.post("/v1/events", json=invalid_payload)
    assert response.status_code == 422  # Validation Error
