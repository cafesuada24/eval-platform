"""AI judge service implementations."""

import litellm
from app.core.eval_engine.models import JudgeResult, Metric
from app.core.eval_engine.ports import AIJudgeService
from pydantic import TypeAdapter


def _get_litellm_model_name(config: Metric) -> str:
    """Format provider and model name properly for litellm.

    e.g., 'anthropic/claude-3-5-sonnet' or 'google/gemini-1.5-pro'
    """
    provider = config.model_configuration.provider.lower()
    if provider == 'google':
        provider = 'gemini'
    model = config.model_configuration.model
    if model.lower().startswith(f'{provider}/'):
        return model
    return f'{provider}/{model}'


class LiteLLMAIJudge(AIJudgeService):
    """AI judge backed by LiteLLM."""

    async def evaluate(self, metric: Metric, prompt: str) -> JudgeResult:
        """Call agent to judge against a well formatted prompt."""
        assert metric.type == 'ai-judge'
        sys_instruct = (
            'You are an objective AI evaluation judge. You must evaluate the prompt according to the given criteria.\n'
            'You must return your output ONLY as a JSON object with two fields:\n'
            f'- "score": A numeric value representing the score. This value MUST be a {metric.scoring_scale.data_type}'
            f' between {metric.scoring_scale.min} and {metric.scoring_scale.max} (inclusive).\n'
            '- "justification": A clear, concise text justification explaining why you gave this score.\n'
            'Do not include any markdown styling, conversational filler, or extra text. Output ONLY the raw valid JSON.'
        )

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
            response_format={
                'type': 'json_schema',
                'json_schema': ta.json_schema(),
                'strict': True,
            },
            temperature=temperature,
        )

        content = response.choices[0].message.content

        return ta.validate_json(content)
