# Backend Implementation Plan

**Objective:** Build a FastAPI backend capable of ingesting high-throughput telemetry, resolving variables autonomously, orchestrating LiteLLM evaluations, and asserting semantic threshold rules.

## Phase 1: Data Contracts & YAML Fixtures
**Goal:** Establish the strict type boundaries for the system.

1.  **Telemetry Models (`app/models/telemetry.py`)**:
    * Create `RuntimeEvent`: `event_id`, `trace_id`, `event_type`, `timestamp`, `payload`, `metadata`.
    * Create `RuntimeState`: `trace_id`, `input_text`, `output_text`, `resource_usage`, `artifacts`, `metadata`.
2.  **Report Models (`app/models/report.py`)**: 
    * Create `MetricRunResult` (BaseModel): `metric_name` (str), `score` (float), `justification` (str), `assertion_status` (Literal["pass", "fail", "warning"]).
    * Create `PipelineResult` (BaseModel): `trace_id` (str), `pipeline_name` (str), `overall_status` (Literal["pass", "fail", "warning"]), `metric_results` (List[MetricRunResult]).
2.  **Threshold & Config Models (`app/models/config.py`)**:
    * Create `MetricConfig`: `name`, `type`, `description` (str), `model_configuration`, `required_inputs`, `prompt_template`, `scoring_scale` (min, max, data_type).
    * Create `ThresholdConfig` (BaseModel): Fields should be optional floats: `fail_over`, `fail_below`, `warning_over`, `warning_below`.
    * Create `PipelineMetric` (BaseModel): `metric_name` (str), `threshold` (Optional[ThresholdConfig]).
    * Create `PipelineConfig`: `name` (str), `metrics` (List[PipelineMetric]).
3.  **Reference Fixtures (`fixtures/metrics/` & `fixtures/pipelines/`)**:
    * Write `hallucination_judge.yaml`:
    ```yaml
      name: "hallucination_ai_judge"
      type: "ai-judge"
      description: "Evaluates if the output_text is strictly grounded in the retrieved_context."
      model_configuration:
        provider: "anthropic"
        model: "claude-3-5-sonnet"
      required_inputs:
        - "output_text"
        - "retrieved_context"
      scoring_scale:
        min: 1
        max: 5
        data_type: "integer"
      prompt_template: |
        Analyze if the following statement is fully grounded in the provided context...
      ```
    * Write `rag_pipeline.yaml` implementing the semantic threshold schema:
    ```yaml
      name: "customer_support_rag_eval"
      metrics:
        - metric_name: "hallucination_ai_judge"
          threshold:
            fail_over: 3.5
            warning_over: 2.0
      ```

---

## Phase 2: Asynchronous Ingestion API
**Goal:** Create a non-blocking endpoint to receive telemetry batches.

1.  **API Router (`app/api/routes/events.py`)**:
    * Implement `POST /v1/events` accepting `List[RuntimeEvent]`.
    * Utilize FastAPI's `BackgroundTasks` to process payloads asynchronously.
    * Return `202 Accepted` immediately.

---

## Phase 3: The Autonomous Resolver Engine
**Goal:** Extract variables natively based on agent selections and serialize complex data.

1.  **Function-Based Extractor Registry (`app/engine/resolver.py`)**:
    * Define extractor functions (e.g., `extract_retrieved_context(state)`).
    * Define `SYSTEM_EXTRACTOR_REGISTRY` mapping known variables (e.g., `input_text`, `latency_ms`, `retrieved_context`) to functions.
2.  **LLM Serialization & Resolution**:
    * Write `serialize_for_llm(value: Any) -> str`.
    * Write `resolve_bindings(state: RuntimeState, required_inputs: List[str]) -> Dict[str, str]`.
    * **Logic:** Loop through `required_inputs`. Execute the mapped function from `SYSTEM_EXTRACTOR_REGISTRY`. If missing, raise a critical `ValueError` (invalid variable hallucinated by agent). Run result through `serialize_for_llm()`.
    * Write `format_prompt()` to inject the serialized dictionary into the Jinja2 template.

---

## Phase 4: Execution & Assertion Engine
**Goal:** Execute prompts via LiteLLM and evaluate scores against semantic threshold rules.

1.  **Execution via LiteLLM (`app/engine/executor.py`)**:
    * Define `JudgeOutput(BaseModel)`: `score` (float), `justification` (str).
    * Write `execute_ai_judge(config, prompt) -> JudgeOutput`.
    * Append `SYSTEM_TEMPLATE` (enforcing JSON and numeric bounds based on `data_type`) to the resolved prompt. Call `litellm.completion(response_format={"type": "json_object"})`.
2.  **Threshold Assertion Logic (`app/engine/asserter.py`)**:
    * Define `AssertionResult` (Literal[`"pass"`, `"fail"`, `"warning"`]).
    * Write `evaluate_threshold(score: float, threshold: Optional[ThresholdConfig]) -> AssertionResult`.
    * Evaluate rules in order of severity (check `fail_over`/`fail_below` first. If passed, check `warning_over`/`warning_below`). Return `"pass"` if no boundaries are breached.

---

## Phase 5: The Pipeline Orchestrator

**Goal:** Glue the resolver, executor, and asserter together into a single, highly concurrent pipeline runner.

* **Target File:** `backend/app/engine/orchestrator.py`
* **Dependencies:** `asyncio`, `litellm` (using `acompletion` instead of synchronous `completion`)
* **Implementation Directives:**
* Write an internal `async def _run_single_metric(state: RuntimeState, metric_item: PipelineMetric) -> MetricRunResult`:
    1. Fetch the full `MetricConfig` from the database/YAML using `metric_item.metric_name`.
    2. Call `resolve_bindings(state, config.required_inputs)`.
    3. Call `format_prompt()`.
    4. Call `await execute_ai_judge_async()` (ensure the LiteLLM executor is refactored to use `litellm.acompletion`).
    5. Call `evaluate_threshold(score, metric_item.threshold)`.
    6. Return the packaged `MetricRunResult`.

* Write the public `async def execute_pipeline(state: RuntimeState, pipeline: PipelineConfig) -> PipelineResult`:
    1. Use `asyncio.gather(*tasks)` to execute `_run_single_metric` for every metric in the pipeline **concurrently**. (If a pipeline has 5 metrics, they should all hit the LLM provider at the exact same time to minimize latency).
    2. Iterate over the returned `MetricRunResult` list to determine the `overall_status`.
    3. **Logic:** If *any* metric is `"fail"`, the pipeline is `"fail"`. Else, if *any* metric is `"warning"`, the pipeline is `"warning"`. Otherwise, `"pass"`.
    4. Return the fully compiled `PipelineResult`.

---

## Phase 6: Internal Metric Agent Service
**Goal:** Expose a Google GenAI service for autonomous metric creation driven by YAML context.

1.  **Tool Definition (`app/services/metric_agent.py`)**:
    * Define `UpdateMetricConfigTool(BaseModel)` matching the `MetricConfig` UI form parameters (including `description`).
2.  **Agent Invocation**:
    * Initialize the `google-genai` client.
    * Write `chat_with_agent(messages: list, current_yaml_config: str = None)`.
    * **Dynamic Context Injection:**
```python
      system_instruction = f"""
      You are an expert AI Metric Builder.
      
      CRITICAL RULES:
      1. You must autonomously decide which system variables are required.
      2. You MUST select variables ONLY from this exact list: {list(SYSTEM_EXTRACTOR_REGISTRY.keys())}. Do not invent variables.
      3. Write the Jinja2 template using your selected variables, write a clear metric `description`, and invoke UpdateMetricConfigTool.
      """
      
      if current_yaml_config:
          system_instruction += f"\nCURRENT METRIC STATE:\n```yaml\n{current_yaml_config}\n```"
```

---
