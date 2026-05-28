import time
from datetime import datetime, timezone
import pytest
import respx
import httpx
from evalplatform_sdk.client import EvalClient
from evalplatform_sdk.models import RuntimeEvent

@pytest.fixture
def mock_event():
    return RuntimeEvent(
        event_id="e1",
        trace_id="t1",
        event_type="test",
        timestamp=datetime.now(timezone.utc),
        payload={"key": "value"}
    )

def test_client_initialization():
    client = EvalClient(api_key="test_key", base_url="http://test.com")
    assert client.api_key == "test_key"
    assert client.base_url == "http://test.com"
    assert client.max_buffer_size == 50
    assert client._buffer == []
    client.flush_sync()

@respx.mock
def test_client_flush_on_max_size(mock_event):
    respx.post("http://test.com/v1/events").respond(status_code=200)
    
    # Use a long interval so it only flushes on max_size
    client = EvalClient(
        api_key="test",
        base_url="http://test.com",
        flush_interval_seconds=10.0,
        max_buffer_size=2
    )
    
    client.log_event(mock_event)
    assert len(client._buffer) == 1
    
    client.log_event(mock_event)
    # The second event should trigger the flush
    # Give the background thread a moment to process
    time.sleep(0.1)
    
    assert len(client._buffer) == 0
    assert respx.calls.call_count == 1
    
    # Cleanup
    client.flush_sync()

@respx.mock
def test_client_flush_on_interval(mock_event):
    respx.post("http://test.com/v1/events").respond(status_code=200)
    
    client = EvalClient(
        api_key="test",
        base_url="http://test.com",
        flush_interval_seconds=0.1,
        max_buffer_size=10
    )
    
    client.log_event(mock_event)
    assert len(client._buffer) == 1
    
    # Wait for the interval to pass
    time.sleep(0.2)
    
    assert len(client._buffer) == 0
    assert respx.calls.call_count == 1
    
    client.flush_sync()

@respx.mock
def test_client_sync_flush(mock_event):
    respx.post("http://test.com/v1/events").respond(status_code=200)
    
    client = EvalClient(
        api_key="test",
        base_url="http://test.com",
        flush_interval_seconds=10.0,
        max_buffer_size=10
    )
    
    client.log_event(mock_event)
    assert len(client._buffer) == 1
    
    client.flush_sync()
    
    assert len(client._buffer) == 0
    assert respx.calls.call_count == 1

def test_client_buffer_capacity_drop(mock_event):
    client = EvalClient(
        api_key="test",
        base_url="http://test.com",
        flush_interval_seconds=10.0,
        max_buffer_size=10,
        max_buffer_capacity=2
    )
    # Stop background thread so it doesn't drain the buffer
    client._stop_event.set()
    
    client.log_event(mock_event)
    client.log_event(mock_event)
    assert len(client._buffer) == 2
    
    # Third event should be dropped
    client.log_event(mock_event)
    assert len(client._buffer) == 2
    
    client._flush_buffer()
    client.flush_sync()
