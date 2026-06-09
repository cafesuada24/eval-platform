"""AI judge service implementations."""

import litellm

litellm.num_retries = 0
from app.core.eval_engine.models import JudgeResult, Metric
from app.core.shared.retry import with_retry
from pydantic import TypeAdapter


def _get_litellm_model_name(config: Metric) -> str:
    """Format provider and model name properly for litellm.

    e.g., 'anthropic/claude-3-5-sonnet' or 'google/gemini-1.5-pro'
    """
    if not config.model_configuration:
        return 'openai/gpt-4o'
    provider = config.model_configuration.provider.lower()
    if provider == 'google':
        provider = 'gemini'
    model = config.model_configuration.model
    if '/' in model:
        # Already prefixed
        return model
    return f'{provider}/{model}'


class LiteLLMAIJudge:
    """AI judge backed by LiteLLM."""

    def __init__(self) -> None:
        litellm.drop_params = True
        litellm.num_retries = 0

    @with_retry()
    async def evaluate(
        self,
        metric: Metric,
        prompt: str,
        building_mode: bool = False,
    ) -> JudgeResult:
        """Call agent to judge against a well formatted prompt."""
        assert metric.type == 'ai-judge'
        improvement = (
            '* **"improvements"**: Actionable and specific suggestions on how the user can refine their evaluation prompt to achieve higher aligment with there intent.'
            if building_mode
            else ''
        )
        sys_instruct = f"""<role>
You are an **objective AI evaluation judge**. Your task is to evaluate the provided input strictly according to the given criteria.
</role>

<instructions>
To ensure a rigorous and detailed evaluation, you must follow a step-by-step reasoning process **BEFORE** assigning a score.
You MUST return your output ONLY as a JSON object. Do not include any markdown styling for the code block (such as ```json), conversational filler, or extra text. Output ONLY the raw, valid JSON.
You MUST respond in user's language.
</instructions>

<output_contract>
The JSON object MUST contain exactly these four fields in this EXACT order:
* **"evidence"**: Bullet points quoting specific parts of the evaluated text that directly relate to the criteria.
* **"justification"**: Bullet points detailed, step-by-step reasoning explaining how the extracted evidence aligns or fails to align with the criteria.
* **"score"**: A numeric value representing the final score. This value MUST be a {metric.scoring_scale.data_type} between {metric.scoring_scale.min} and {metric.scoring_scale.max} (inclusive).
{improvement}
</output_contract>"""

        model_name = _get_litellm_model_name(metric)
        temperature = metric.model_configuration.temperature

        messages = [
            {'role': 'system', 'content': sys_instruct},
            {'role': 'user', 'content': prompt},
        ]

        ta = TypeAdapter(JudgeResult)


        response = await litellm.acompletion(
            model=model_name,
            messages=messages,
            reasoning_effort='high',
            response_format={
                'type': 'json_schema',
                'json_schema': ta.json_schema(),
                'strict': True,
            },
            temperature=temperature,
            num_retries=0,
        )

        content = response.choices[0].message.content

        return ta.validate_json(content)
