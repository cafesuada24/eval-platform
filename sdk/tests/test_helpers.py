import asyncio
import time
from typing import Any

import pytest
import respx
from evalplatform_sdk.client import EvalClient, _default_client
from evalplatform_sdk.helpers import capture_trace, trace
import evalplatform_sdk.client as client_module


@pytest.fixture(autouse=True)
def reset_default_client():
    client_module._default_client = None
    yield
    client_module._default_client = None


@pytest.fixture
def test_client():
    client = EvalClient(api_key="test", base_url="http://test.com")
    return client


def test_trace_context_manager(test_client):
    with trace(trace_id="test-trace-1") as state:
        state.input_text = "hello"
        time.sleep(0.01)
        state.output_text = "world"

    assert len(test_client._buffer) == 1
    event = test_client._buffer[0]
    
    assert event.trace_id == "test-trace-1"
    assert event.event_type == "trace.completed"
    
    payload = event.payload
    assert payload["input_text"] == "hello"
    assert payload["output_text"] == "world"
    assert "latency_ms" in payload["resource_usage"]
    assert payload["resource_usage"]["latency_ms"] >= 10.0


def test_capture_trace_sync(test_client):
    @capture_trace
    def generate_text(input_text: str, temperature: float = 0.5) -> str:
        time.sleep(0.01)
        return f"Response to: {input_text}"

    result = generate_text(input_text="Hi there", temperature=0.7, trace_id="trace-sync")
    
    assert result == "Response to: Hi there"
    assert len(test_client._buffer) == 1
    
    event = test_client._buffer[0]
    assert event.trace_id == "trace-sync"
    
    payload = event.payload
    assert payload["input_text"] == "Hi there"
    assert payload["output_text"] == "Response to: Hi there"
    assert payload["metadata"]["temperature"] == 0.7
    assert payload["resource_usage"]["latency_ms"] >= 10.0


@pytest.mark.asyncio
async def test_capture_trace_async(test_client):
    @capture_trace
    async def async_generate(input_text: str, model: str) -> dict:
        await asyncio.sleep(0.01)
        return {"answer": f"Async response to: {input_text}"}

    result = await async_generate(input_text="Hello async", model="gpt-4", trace_id="trace-async")
    
    assert result["answer"] == "Async response to: Hello async"
    assert len(test_client._buffer) == 1
    
    event = test_client._buffer[0]
    assert event.trace_id == "trace-async"
    
    payload = event.payload
    assert payload["input_text"] == "Hello async"
    assert "output" in payload["metadata"]
    assert "Async response to" in payload["metadata"]["output"]
    assert payload["metadata"]["model"] == "gpt-4"
    assert payload["resource_usage"]["latency_ms"] >= 10.0
