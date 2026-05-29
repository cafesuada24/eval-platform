"""Agentic metric builder implementation."""

import os
from string import Template
from typing import Literal

from app.core.entities.chat_session import ChatSession
from app.core.services.runtime_state_extrator import RuntimeStateExtractorService
from app.core.value_objects.agent_response import MetricBuilderAgentResponse
from google import genai
from google.genai import types
from pydantic import TypeAdapter, ValidationError

SYS_INSTRUCTION_TEMPLATE = Template(
    """<instruction>
You are an expert AI Metric Builder.
</instruction>

<allowed_variables>
$allowed_variables
</allowed_variables>

<rules>
1. You must autonomously decide which system variables are required.
2. You MUST select variables ONLY from `allowed_variables` list. Do not invent variables.
3. Return the friendly conversational response in `response_text`, explaining any changes.
4. Return the complete, updated structured MetricConfig in `updated_metric`. If the user is creating or modifying a metric,
ensure that `updated_metric` represents the complete draft configuration with all fields populated appropriately.
</rules>

<response_contract>
{
    "response_text": "Friendly response",
    "updated_metric": "MetricConfig"
}
</response_contract>
""",
)

class Event:
    """An event."""
    type: Literal['direct_answer', '']

class Thread:
    events: list[Event]

class GeminiAgenticBuilder:
    """Agentic builder backed by gemini."""

    def __init__(self, model: str = 'gemini-3.1-flash-lite') -> None:
        self.__model = model
        self.__client = genai.Client(
            api_key=os.getenv('GOOGLE_API_KEY'),
        )

    async def chat(
        self,
        session: ChatSession,
        current_metric_config: str | None = None,
    ) -> MetricBuilderAgentResponse:
        """Query the builder."""
        ta = TypeAdapter(MetricBuilderAgentResponse)
        raw_schema = ta.json_schema()

        allowed_vars = '\n -'.join(
            list(
                RuntimeStateExtractorService.get_supported_runtime_variables(),
            ),
        )

        system_instruction = SYS_INSTRUCTION_TEMPLATE.substitute(
            allowed_vars=allowed_vars,
        )

        if current_metric_config:
            system_instruction += f'\n<current_metric_state>\n```yaml\n{current_metric_config}\n```\n</current_metric_state>'

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type='application/json',
            response_schema=raw_schema,
        )

        formatted_contents: list[types.Content] = []
        for msg in session.messages:
            formatted_contents.append(
                types.Content(
                    role=msg['role'],
                    parts=[types.Part.from_text(text=msg['content'])],
                ),
            )

        response = await self.__client.aio.models.generate_content(
            model=self.__model,
            contents=formatted_contents,
            config=config,
        )
        if response.text is None:
            return MetricBuilderAgentResponse(
                response_text='Sorry. Agent returned an empty response.',
                updated_metric=None,
            )
        updated_metric = None
        try:
            parsed_data = ta.validate_json(response.text)
            response_text = parsed_data.response_text
            updated_metric = parsed_data.updated_metric

        except ValidationError:
            response_text = response.text

        return MetricBuilderAgentResponse(
            response_text=response_text,
            updated_metric=updated_metric,
        )
