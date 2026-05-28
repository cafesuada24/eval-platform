import json
from typing import Any

from app.engine.resolver import SYSTEM_EXTRACTOR_REGISTRY
from app.models.config import MetricConfig
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class MetricBuilderResponse(BaseModel):
    response_text: str = Field(
        description="The friendly conversational response to the user, answering their questions, providing context, or explaining changes."
    )
    updated_metric: MetricConfig | None = Field(
        default=None,
        description="The complete structured MetricConfig draft, if a metric is being created or updated. Return None if no metric is under discussion or if no changes were made."
    )


def remove_additional_properties(schema: Any) -> Any:
    """Recursively removes the 'additionalProperties' key from a JSON schema dictionary."""
    if isinstance(schema, dict):
        schema.pop("additionalProperties", None)
        return {k: remove_additional_properties(v) for k, v in schema.items()}
    elif isinstance(schema, list):
        return [remove_additional_properties(item) for item in schema]
    return schema


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
        and enforces structured JSON output matching MetricBuilderResponse.
        """
        allowed_vars = list(SYSTEM_EXTRACTOR_REGISTRY.keys())

        system_instruction = (
            'You are an expert AI Metric Builder.\n\n'
            'CRITICAL RULES:\n'
            '1. You must autonomously decide which system variables are required.\n'
            f'2. You MUST select variables ONLY from this exact list: {allowed_vars}. Do not invent variables.\n'
            '3. Return the friendly conversational response in `response_text`, explaining any changes.\n'
            '4. Return the complete, updated structured MetricConfig in `updated_metric`. If the user is creating or modifying a metric, '
            'ensure that `updated_metric` represents the complete draft configuration with all fields populated appropriately.\n'
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

        from pydantic import TypeAdapter
        raw_schema = TypeAdapter(MetricBuilderResponse).json_schema()
        clean_schema = remove_additional_properties(raw_schema)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=clean_schema,
        )

        response = self.client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=formatted_contents,
            config=config,
        )

        try:
            parsed_data = json.loads(response.text)
            response_text = parsed_data.get("response_text", "")
            updated_metric = parsed_data.get("updated_metric")
        except Exception:
            response_text = response.text
            updated_metric = None

        return {
            'response_text': response_text,
            'updated_metric': updated_metric,
        }
