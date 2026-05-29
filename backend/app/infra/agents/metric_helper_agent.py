"""Agentic metric helper implementation."""

import os
import time
from string import Template

from app.core.agents.metric_helper.models import (
    AgentEvent,
    ChatMessage,
    ChatSession,
    CreateOrUpdateMetricEvent,
    MetricDraft,
    MetricHelperResponse,
    QueryDocumentsEvent,
    Thread,
)
from app.core.agents.metric_helper.utils import thread_to_prompt
from app.core.eval_engine.extractors.runtime_state_extractor import (
    RuntimeStateExtractorService,
)
from app.core.kernel.builders.runtime_builder import RuntimeStateBuilder
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
    ) -> MetricHelperResponse:
        """Query the builder."""
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

        return await self.__run_agent_loop(
            system_instruction=system_instruction,
            messages=session.messages,
        )

    async def __run_agent_loop(
        self,
        system_instruction: str,
        messages: list[ChatMessage],
    ) -> MetricHelperResponse:
        if not messages:
            raise ValueError("Messages list cannot be empty.")

        runtime_builder = RuntimeStateBuilder()

        ta = TypeAdapter(AgentEvent)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type='application/json',
            response_schema=ta.json_schema(),
        )

        formatted_contents: list[types.Content] = [
            types.Content(
                role=msg.role,
                parts=[types.Part.from_text(text=msg.content)],
            )
            for msg in messages
        ]

        thread = Thread(
            [
                AgentEvent(
                    type='user_message',
                    data=messages[-1].content,
                ),
            ],
        )

        runtime_builder.event(
            'generation.started',
            payload={
                'provider': 'google',
                'model': self.__model,
                'input_text': messages[-1].content,
            },
        )

        response_text: str
        metric_draft: MetricDraft | None = None
        input_tokens = 0
        output_tokens = 0

        start = time.perf_counter()

        steps = 0

        while True:
            steps += 1

            thread_yaml = thread_to_prompt(thread)
            msg = (
                "Here's everything that happened so far:\n\n"
                f'{thread_yaml}\n\n'
                "What's the next step?"
            )

            formatted_contents[-1] = types.Content(
                role='user',
                parts=[types.Part.from_text(text=msg)],
            )

            response = await self.__client.aio.models.generate_content(
                model=self.__model,
                contents=formatted_contents,
                config=config,
            )
            if response.usage_metadata is not None:
                input_tokens += response.usage_metadata.prompt_token_count or 0
                output_tokens += response.usage_metadata.candidates_token_count or 0

            if response.text is None:
                raise RuntimeError('Agent returned a null message.')

            try:
                ev = ta.validate_json(response.text)
            except ValidationError as e:
                # TODO: do some useful things
                raise

            if ev.type == 'response':
                assert isinstance(ev.data, str)
                response_text = ev.data
                break

            if ev.type == 'create_or_update_metric':
                assert isinstance(ev.data, CreateOrUpdateMetricEvent)
                response_text = ev.data.response
                metric_draft = ev.data.metric_draft
                break

            if ev.type == 'query_documents':
                assert isinstance(ev.data, QueryDocumentsEvent)
                # TODO: implement real RAG mechanism
                # runtime_builder.event('retrieval.started', {'query': ev.data.query})
                # Query...
                # runtime_builder.event('retrieval.completed', {'query': ev.data.query, 'chunks': ...})
                # thread.events.append(
                #     AgentEvent(
                #         type='query_documents_result',
                #         data=QueryDocumentsResultEvent(query_result=...),
                #     ),
                # )

        delta = time.perf_counter() - start

        runtime_builder.event(
            'generation.completed',
            {'output_text': response_text, 'steps': steps},
        )
        runtime_builder.token_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        runtime_builder.latency_ms(int(delta))
        runtime = runtime_builder.build()
        return MetricHelperResponse(
            response_text=response_text,
            metric_draft=metric_draft,
            runtime_id=runtime.runtime_id,
        )
