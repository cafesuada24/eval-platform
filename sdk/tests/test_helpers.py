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
    with trace(runtime_id="test-trace-1") as state:
        state.input_text = "hello"
        time.sleep(0.01)
        state.output_text = "world"

    assert len(test_client._buffer) == 1
    state_out = test_client._buffer[0]
    
    assert state_out.runtime_id == "test-trace-1"
    assert state_out.input_text == "hello"
    assert state_out.output_text == "world"
    assert state_out.usage.latency_ms >= 10.0


def test_capture_trace_sync(test_client):
    @capture_trace
    def generate_text(input_text: str, temperature: float = 0.5) -> str:
        time.sleep(0.01)
        return f"Response to: {input_text}"

    result = generate_text(input_text="Hi there", temperature=0.7, runtime_id="trace-sync")
    
    assert result == "Response to: Hi there"
    assert len(test_client._buffer) == 1
    
    state = test_client._buffer[0]
    assert state.runtime_id == "trace-sync"
    assert state.input_text == "Hi there"
    assert state.output_text == "Response to: Hi there"
    assert state.metadata["temperature"] == 0.7
    assert state.usage.latency_ms >= 10.0


@pytest.mark.asyncio
async def test_capture_trace_async(test_client):
    @capture_trace
    async def async_generate(input_text: str, model: str) -> dict:
        await asyncio.sleep(0.01)
        return {"answer": f"Async response to: {input_text}"}

    result = await async_generate(input_text="Hello async", model="gpt-4", runtime_id="trace-async")
    
    assert result["answer"] == "Async response to: Hello async"
    assert len(test_client._buffer) == 1
    
    state = test_client._buffer[0]
    assert state.runtime_id == "trace-async"
    assert state.input_text == "Hello async"
    assert "Async response to" in state.metadata["output"]["answer"]
    assert state.metadata["model"] == "gpt-4"
    assert state.usage.latency_ms >= 10.0


def test_capture_trace_generator(test_client):
    @capture_trace
    def stream_text(input_text: str):
        time.sleep(0.005)
        yield "Hello "
        time.sleep(0.005)
        yield "world"
        
    result = list(stream_text(input_text="greet", runtime_id="trace-stream"))
    assert result == ["Hello ", "world"]
    assert len(test_client._buffer) == 1
    
    state = test_client._buffer[0]
    assert state.runtime_id == "trace-stream"
    assert state.input_text == "greet"
    assert state.output_text == "Hello world"
    assert state.usage.latency_ms >= 10.0

