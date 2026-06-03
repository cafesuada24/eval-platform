# EvalPlatform Python SDK

> The lightweight, non-blocking telemetry capture client and management API wrapper for the EvalPlatform ecosystem.

The EvalPlatform Python SDK provides two core capabilities:
1. **Telemetry Capture:** Zero-overhead, background logging for your AI applications using high-level decorators or context managers.
2. **Management API:** A synchronous client for CI/CD environments to upload golden datasets and trigger offline batch evaluations.

## Quick Start

### Installation

*Ensure you have Python 3.10+ installed.*

```bash
# Example with pip (once published)
pip install evalplatform_sdk
```

### Initialization

Before using any of the helpers or management features, you must initialize the `EvalClient` singleton.

```python
from evalplatform_sdk.client import EvalClient

client = EvalClient(
    api_key="your_api_key_here",
    base_url="http://localhost:8000"
)
```

By default, the client spins up a background thread that flushes telemetry events to the backend every 3.0 seconds, ensuring your host application's performance never degrades.

---

## 1. Telemetry Capture

The SDK provides high-level helpers in the `helpers` module to effortlessly trace your application.

### Using the `@capture_trace` Decorator

The easiest way to trace a function is with the `@capture_trace` decorator. It works on both synchronous and asynchronous functions. It will automatically calculate latency, capture inputs, and capture outputs.

```python
from evalplatform_sdk.helpers import capture_trace

@capture_trace
def generate_response(input_text: str, temperature: float = 0.7):
    # Your LLM call or business logic here
    return f"Response to: {input_text}"

# The SDK automatically captures `input_text`, `temperature` (as metadata), 
# the string return value, and calculates execution latency.
result = generate_response(input_text="Hello world!", temperature=0.9)
```

### Using the `with trace()` Context Manager

If you need more fine-grained control over the `RuntimeState` (for instance, to attach multimodal artifacts, update metadata mid-execution, or track LLM generation metrics), use the `trace` context manager:

```python
from evalplatform_sdk.helpers import trace
from evalplatform_sdk.models import Artifact

def complex_generation(query: str):
    with trace() as state:
        state.input_text = query
        
        # ... fetch context from DB ...
        state.metadata = {"retrieved_context": "Sample DB context"}
        
        # ... attach an artifact ...
        image_artifact = Artifact(type="image/ocr", content="Extracted text from image")
        state.artifacts = [image_artifact]
        
        # Track an LLM generation call's latency and tokens
        with state.track_generation(model="gpt-4") as tracker:
            # Your LLM call here
            state.output_text = "Generated successfully."
            tracker.input_tokens = 150
            tracker.output_tokens = 25
            
        return state.output_text
```

### Manual Logging

For total control, you can construct and dispatch `RuntimeEvent` objects manually via the client instance:

```python
import uuid
from datetime import datetime, UTC
from evalplatform_sdk.models import RuntimeEvent

event = RuntimeEvent(
    event_id=str(uuid.uuid4()),
    trace_id="my_custom_trace",
    event_type="custom.event",
    timestamp=datetime.now(UTC),
    payload={"key": "value"}
)
client.log_event(event)
```

---

## 2. Management APIs (Offline Evaluation)

The SDK acts as a "Fat Client" and includes synchronous management APIs. These are perfect for CI/CD pipelines where you want to upload test cases and run evaluations programmatically. 

These operations utilize a dedicated HTTP client with a longer timeout (30s) to safely handle file uploads without disrupting background telemetry.

### Managing Datasets

You can upload JSON and CSV files to be used as golden datasets:

```python
# Upload a JSON dataset
dataset = client.datasets.upload_json("My Golden JSON Set", "./path/to/dataset.json")
print(f"Uploaded JSON Dataset ID: {dataset['id']}")

# Upload a CSV dataset
csv_dataset = client.datasets.upload_csv("My Golden CSV Set", "./path/to/dataset.csv")
print(f"Uploaded CSV Dataset ID: {csv_dataset['id']}")
```

### Client-Driven Evaluations

Once you have a dataset and a configured evaluation pipeline on your backend, you can start an evaluation and run it locally. The SDK will automatically track and link your telemetry to the evaluation test cases.

```python
pipeline_id = "your-pipeline-uuid"
dataset_id = dataset["id"]

# Retrieve the test cases from the uploaded dataset
cases = client.datasets.get_cases(dataset_id)

# Start an evaluation context
with client.pipelines.start_evaluation(pipeline_id, dataset_id) as evaluation:
    for case in cases:
        # track_case automatically links nested trace() calls to this test case
        with evaluation.track_case(case["id"]):
            # Your application logic here, using @capture_trace or trace()
            result = generate_response(input_text=case.get("input", ""))
            print(f"Evaluated case {case['id']} with result: {result}")
```

---

## Shutdown & Teardown

When your application terminates, the SDK uses `atexit` to automatically flush any remaining telemetry events from the in-memory buffer. However, you can manually trigger a synchronous flush if needed:

```python
client.flush_sync()
```
