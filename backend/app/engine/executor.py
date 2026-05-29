import json

import litellm
from app.models.config import MetricConfig
from pydantic import BaseModel


class JudgeOutput(BaseModel):
    score: float
    justification: str


def get_litellm_model_name(config: MetricConfig) -> str:
    """Format provider and model name properly for litellm.

    e.g., 'anthropic/claude-3-5-sonnet' or 'google/gemini-1.5-pro'
    """
    provider = config.model_configuration.provider.lower()
    model = config.model_configuration.model
    if model.lower().startswith(f'{provider}/'):
        return model
    return f'{provider}/{model}'


def get_system_instruction(config: MetricConfig) -> str:
    """Generate dynamic system instructions enforcing output structure and constraints."""
    min_val = config.scoring_scale.min
    max_val = config.scoring_scale.max
    data_type = config.scoring_scale.data_type

    return (
        'You are an objective AI evaluation judge. You must evaluate the prompt according to the given criteria.\n'
        'You must return your output ONLY as a JSON object with two fields:\n'
        f'- "score": A numeric value representing the score. This value MUST be a {data_type} between {min_val} and {max_val} (inclusive).\n'
        '- "justification": A clear, concise text justification explaining why you gave this score.\n'
        'Do not include any markdown styling, conversational filler, or extra text. Output ONLY the raw valid JSON.'
    )


def execute_ai_judge(config: MetricConfig, prompt: str) -> JudgeOutput:
    """Synchronously execute the evaluation metric prompt via LiteLLM.

    Enforces a JSON object response format.
    """
    model_name = get_litellm_model_name(config)
    system_instruction = get_system_instruction(config)
    temperature = (
        config.model_configuration.temperature
        if config.model_configuration is not None
        else 0.2
    )

    messages = [
        {'role': 'system', 'content': system_instruction},
        {'role': 'user', 'content': prompt},
    ]

    response = litellm.completion(
        model=model_name,
        messages=messages,
        response_format={'type': 'json_object'},
        temperature=temperature,
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return JudgeOutput(**data)


async def execute_ai_judge_async(config: MetricConfig, prompt: str) -> JudgeOutput:
    """Asynchronously execute the evaluation metric prompt via LiteLLM acompletion.
    Enforces a JSON object response format.
    """
    model_name = get_litellm_model_name(config)
    system_instruction = get_system_instruction(config)
    temperature = (
        config.model_configuration.temperature
        if config.model_configuration is not None
        else 0.2
    )

    messages = [
        {'role': 'system', 'content': system_instruction},
        {'role': 'user', 'content': prompt},
    ]

    response = await litellm.acompletion(
        model=model_name,
        messages=messages,
        response_format={'type': 'json_object'},
        temperature=temperature,
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return JudgeOutput(**data)
