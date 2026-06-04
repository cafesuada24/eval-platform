# Tracking Telemetry in EvalPlatform SDK

The EvalPlatform SDK relies exclusively on clean, context-manager-driven workflows to track your execution telemetry. All tracking happens entirely in-memory and is dispatched asynchronously in the background so your application remains non-blocking.

## Quick Start

The core tracking object is the `trace()` context manager. It automatically calculates the overall latency of the block and submits the resulting `RuntimeState` to the backend when the block exits.

```python
from evalplatform_sdk.client import EvalClient
from evalplatform_sdk.helpers import trace

# Initialize the client globally (starts background worker)
client = EvalClient(api_key="your-api-key", base_url="http://localhost:8000")

# Start tracking an execution trace
with trace() as state:
    
    # Your business logic goes here
    result = "Hello World"
    
    # Record total usage
    state.usage.input_tokens = 100
    state.usage.output_tokens = 10
```

---

## Tracking Sub-Events
Inside a `trace`, you can track granular sub-events like OCR, Vector DB retrievals, and LLM generations. These events are tightly bound to the parent trace.

### 1. File Processing (OCR / Parsers)
Track operations where files are ingested and converted to text.

```python
with state.track_file_processed() as file_tracker:
    # 1. Define what is being processed
    file_tracker.file_info(file_name="invoice.pdf", processor="ocr")
    
    # ... your application logic ...
    extracted_text = my_ocr_service.read("invoice.pdf")
    
    # 2. Log the output
    file_tracker.content(extracted_text)
    
    # Note: Latency is automatically calculated for you!
```

### 2. Document Retrieval (RAG)
Track operations where a query retrieves semantic chunks from a vector database.

```python
with state.track_retrieval() as retrieval_tracker:
    # 1. Define the search query
    retrieval_tracker.query("What is the total amount due?")
    
    # ... your application logic ...
    results = vector_db.search("What is the total amount due?")
    
    # 2. Append the retrieved chunks
    for res in results:
        retrieval_tracker.add_chunk(
            document=res.file_name, 
            content=res.text, 
            confidence=res.score
        )
```

### 3. LLM Generation
Track actual prompts being sent to LLMs and their resulting outputs.

```python
with state.track_generation() as gen_tracker:
    # 1. Define the model
    gen_tracker.model_info(provider="openai", model_name="gpt-4o")
    
    # 2. Define the input
    gen_tracker.user_input("Extract the total amount from the retrieved context.")
    
    # ... your application logic ...
    response = llm.generate(...)
    
    # 3. Log token usage
    gen_tracker.token_usage(
        input_tokens=response.prompt_tokens, 
        output_tokens=response.completion_tokens
    )
```

---

## Batch Evaluation Integration
If you are iterating through a dataset for evaluation, you can bind your traces to a specific `testcase_id` by using the `Evaluation` context managers.

EvalPlatform enforces **Strict Explicit Tracking**. Traces are never automatically swept into an evaluation context. You must explicitly pass the `CaseTracker` to the `trace()` function to bind it. This prevents unrelated background tasks or unrelated system modules from polluting the evaluation dataset!

```python
# 1. Start an evaluation job
evaluation = client.pipelines.start_evaluation(
    pipeline_id="pipe_abc", 
    dataset_id="dataset_123"
)

for case in cases:
    
    # 2. Start tracking for this specific dataset row
    with evaluation.track_case(case["id"]) as case_tracker:
        
        # 3. Execute your logic and pass the case_tracker explicitly!
        with trace(eval_tracker=case_tracker) as state:
            
            with state.track_retrieval() as rt:
                rt.query(case["question"])
                # ...
                
            with state.track_generation() as gt:
                gt.user_input(case["question"])
                # ...

# 4. Non-blocking evaluation completion
evaluation.complete(block=False)
```

## Structure Principles
- **Explicit Binding:** You always remain in control over what gets sent to the standard telemetry pipeline vs the evaluation test case scoring pipeline.
- **Scannable:** Use context managers (`with state.track_...()`) to visually delineate the boundaries of different telemetry phases in your code.
- **Automated Latency:** You do not need to pass timestamps. Latency is automatically calculated by the entry and exit of the context managers.
- **Background Execution:** `EvalClient` batches your traces in-memory and flushes them in a background daemon thread, while `CaseTracker` uses a `ThreadPoolExecutor` to dispatch testcases cleanly. Your application will not experience network blocking delays.
