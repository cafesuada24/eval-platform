from typing import Any

from app.engine.resolver import SYSTEM_EXTRACTOR_REGISTRY
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class ModelConfigToolInput(BaseModel):

    provider: str = Field(
        description="The model provider, e.g., 'anthropic' or 'google'"
    )
    model: str = Field(
        description="The model name, e.g., 'claude-3-5-sonnet' or 'gemini-2-flash'"
    )


class ScoringScaleToolInput(BaseModel):
    min: float = Field(description='The minimum possible score value')
    max: float = Field(description='The maximum possible score value')
    data_type: str = Field(
        description="The data type of the score, e.g., 'integer' or 'float'"
    )


class UpdateMetricConfigTool(BaseModel):
    """Form parameters to update or create a MetricConfig."""

    name: str = Field(
        description='The unique name of the metric (e.g., hallucination_ai_judge)'
    )
    type: str = Field(description="The type of the metric (e.g., 'ai-judge')")
    description: str = Field(
        description='A clear description of the metric, explaining what it evaluates'
    )
    model_configuration: ModelConfigToolInput = Field(
        description='Configuration of the model used for evaluation'
    )
    required_inputs: list[str] = Field(
        description='Variables required by the metric template, selected ONLY from SYSTEM_EXTRACTOR_REGISTRY.'
    )
    prompt_template: str = Field(
        description='The Jinja2 prompt template using selected variables'
    )
    scoring_scale: ScoringScaleToolInput = Field(
        description='The minimum/maximum values and type of the metric score'
    )


class MetricAgentService:
    def __init__(self, api_key: str | None = None):
        """Initialize the google-genai client.

        If api_key is omitted, client reads from GEMINI_API_KEY env variable.
        """
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def chat_with_agent(
        self,
        messages: list[dict[str, str]],
        current_yaml_config: str | None = None,
    ) -> dict[str, Any]:
        """Interact with the AI Metric Builder agent.

        Injects the Extractor Registry and the current YAML state into the system instruction,
        and registers the UpdateMetricConfigTool.
        """
        allowed_vars = list(SYSTEM_EXTRACTOR_REGISTRY.keys())

        system_instruction = (
            'You are an expert AI Metric Builder.\n\n'
            'CRITICAL RULES:\n'
            '1. You must autonomously decide which system variables are required.\n'
            f'2. You MUST select variables ONLY from this exact list: {allowed_vars}. Do not invent variables.\n'
            '3. Write the Jinja2 template using your selected variables, write a clear metric `description` explaining the metric, '
            'and invoke UpdateMetricConfigTool to save or update the configuration.\n'
        )

        if current_yaml_config:
            system_instruction += (
                f'\nCURRENT METRIC STATE:\n```yaml\n{current_yaml_config}\n```\n'
            )

        # Format messages into google-genai SDK Content structures
        formatted_contents: list[types.Content] = []
        for msg in messages:
            formatted_contents.append(
                types.Content(
                    role=msg['role'],
                    parts=[types.Part.from_text(text=msg['content'])],
                ),
            )

        called_tool_args = []


        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
        )

        response = self.client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=formatted_contents,
            config=config,
        )

        return {
            'response_text': response.text,
            'called_tool_args': called_tool_args,
        }
