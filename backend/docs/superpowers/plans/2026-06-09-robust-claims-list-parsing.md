# Robust Claims List Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent evaluation failure when LLM responses for rigorous strategies contain markdown formatting or simple text by dynamically enforcing the JSON schema in system prompts and sanitizing markdown wrappers.

**Architecture:** Inject strict JSON formatting instructions and the target Pydantic schema dynamically into system prompts inside the `_call_llm_structured` utility, and implement robust cleaning of markdown code blocks (e.g. ````json ... ````) before validation.

**Tech Stack:** Python, Pydantic, LiteLLM, Pytest

---

### Task 1: Add Robustness Tests for `_call_llm_structured`

**Files:**
- Modify: `backend/tests/core/eval_engine/test_multi_step_evaluators.py`

- [ ] **Step 1: Add unit tests verifying markdown cleaning and prompt validation**

Add this test case at the end of `backend/tests/core/eval_engine/test_multi_step_evaluators.py`:

```python
@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_call_llm_structured_robustness(mock_acompletion):
    from app.core.eval_engine.services.multi_step_evaluators import _call_llm_structured, ClaimsList
    
    # Mock return value wrapped in markdown code blocks
    mock_response = mock_litellm_response('```json\n{"claims": ["Robust claim 1", "Robust claim 2"]}\n```')
    mock_acompletion.return_value = mock_response
    
    metric = Metric(
        name="faithfulness_rigorous",
        description="F",
        type="ai-judge",
        required_inputs=["retrieved_context", "output_text"],
        model_configuration=ModelConfiguration(provider="openai", model="gpt-4o")
    )
    
    result = await _call_llm_structured(
        metric=metric,
        system_prompt="Extract claims.",
        user_prompt="Input text",
        response_schema=ClaimsList
    )
    
    # Assert result is correctly parsed into Pydantic model
    assert isinstance(result, ClaimsList)
    assert result.claims == ["Robust claim 1", "Robust claim 2"]
    
    # Assert system prompt was enhanced with instructions and JSON schema
    called_messages = mock_acompletion.call_args.kwargs["messages"]
    system_message = next(msg for msg in called_messages if msg["role"] == "system")
    assert "You MUST return your output ONLY as a JSON object matching this JSON schema:" in system_message["content"]
    assert '"required": ["claims"]' in system_message["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/eval_engine/test_multi_step_evaluators.py::test_call_llm_structured_robustness -v`
Expected: FAIL with `ValidationError` (since currently it does not clean markdown and does not inject the schema).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/core/eval_engine/test_multi_step_evaluators.py
git commit -m "test: add robustness unit test for _call_llm_structured"
```

---

### Task 2: Implement Dynamic Schema Injection & Response Sanitization

**Files:**
- Modify: `backend/app/core/eval_engine/services/multi_step_evaluators.py`

- [ ] **Step 1: Implement prompt enhancement and response sanitization**

In `backend/app/core/eval_engine/services/multi_step_evaluators.py`, import `json` at the top if not present, and update `_call_llm_structured` as follows:

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

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/core/eval_engine/test_multi_step_evaluators.py -v`
Expected: All 7 tests PASS (including the new robustness test).

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/eval_engine/services/multi_step_evaluators.py
git commit -m "feat: implement prompt schema injection and markdown response sanitization"
```
