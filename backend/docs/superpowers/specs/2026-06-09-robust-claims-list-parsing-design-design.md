# Design Spec: Robust JSON Parsing for Rigorous Evaluation Strategies

## Problem Statement
When running evaluation pipelines with rigorous strategies (such as `faithfulness_rigorous`, `answer_relevancy_rigorous`, and `context_recall_rigorous`), the LLM calls fail with validation errors for models/providers (like Google Gemini or Anthropic Claude) that do not strictly enforce native OpenAI-like JSON schema `response_format`. Because the system prompts do not instruct the model to return JSON or follow a specific schema, these models generate natural language text (e.g., markdown bullet points), causing Pydantic `ValidationError`s.

## Objectives
- Ensure multi-step evaluations work reliably across any LLM provider and model.
- Prevent Pydantic validation errors (`ClaimsList`, `ClaimVerificationResponse`, etc.) when LLMs generate non-JSON content.
- Clean and parse markdown code blocks containing JSON that LLMs frequently output.

## Proposed Changes

### 1. `backend/app/core/eval_engine/services/multi_step_evaluators.py`
Modify `_call_llm_structured` to:
- Inject clear JSON-formatting instructions and the Pydantic model's raw JSON schema into the system prompt.
- Strip markdown block wraps (` ```json ` or ` ``` `) from the completion response.
- Attempt Pydantic validation on the cleaned string.

```python
async def _call_llm_structured(
    metric: Metric,
    system_prompt: str,
    user_prompt: str,
    response_schema: type[BaseModel],
) -> Any:
    """Calls LiteLLM's structured generation with a strict Pydantic JSON schema."""
    import json
    model_name = _get_litellm_model_name(metric)
    temperature = (
        metric.model_configuration.temperature
        if metric.model_configuration
        else 0.0
    )

    ta = TypeAdapter(response_schema)
    schema_str = json.dumps(ta.json_schema())
    
    # Inject JSON schema instructions into system prompt
    enhanced_system_prompt = (
        f"{system_prompt}\n\n"
        "You MUST return your output ONLY as a JSON object matching this JSON schema:\n"
        f"{schema_str}\n\n"
        "Do not include any markdown styling, code block wrappers (such as ```json), conversational filler, or extra text. Output ONLY raw, valid JSON."
    )

    messages = [
        {"role": "system", "content": enhanced_system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = await litellm.acompletion(
        model=model_name,
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": ta.json_schema(),
            "strict": True,
        },
        temperature=temperature,
    )

    if not response.choices or response.choices[0].message.content is None:
        raise ValueError("LLM returned an empty or invalid response")

    content = response.choices[0].message.content.strip()
    
    # Strip markdown wrappers if present
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    return ta.validate_json(content)
```

## Verification & Testing Plan
- Run existing mocked unit tests for multi-step evaluators:
  `uv run pytest tests/core/eval_engine/test_multi_step_evaluators.py`
- Validate that the code formats output correctly and parses successfully.
