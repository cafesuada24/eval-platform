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
    QueryDocumentsResultEvent,
    Thread,
)
from app.core.agents.metric_helper.utils import thread_to_prompt
from app.core.config import settings
from app.core.eval_engine.extractors.runtime_state_extractor import (
    RuntimeStateExtractorService,
)
from app.core.kernel.builders.runtime_builder import RuntimeStateBuilder
from app.core.kernel.ports import RuntimeStateRepository
from app.core.vector_storage.models import QueryResult, RAGParameters
from app.core.vector_storage.ports import VectorStoragePort
from google import genai
from google.genai import types
from pydantic import TypeAdapter, ValidationError


def format_query_results(results: list[QueryResult]) -> str:
    """Helper to convert chunks into an LLM-friendly string format."""
    if not results:
        return 'No relevant documents found.'

    formatted: list[str] = []
    for i, res in enumerate(results):
        doc_name = res.document.metadata.get('filename', res.document.id)
        formatted.append(
            f'--- Document {i + 1} (Source: {doc_name}) ---\n{res.document.text}\n',
        )
    return '\n'.join(formatted)


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
5. You must detect user intent between normal conversation, or updating or create metric. The latter allows you access retrieval tools.
</rules>
""",
)


class GeminiMetricHelper:
    """Agentic builder backed by gemini."""

    def __init__(
        self,
        runtime_state_repo: RuntimeStateRepository | None = None,
        vector_storage: VectorStoragePort | None = None,
        model: str = 'gemini-3.1-flash-lite',
    ) -> None:
        self.__model = model
        self.__runtime_state_repo = runtime_state_repo
        self.__vector_storage = vector_storage
        self.__client = genai.Client(
            api_key=settings.google_api_key or os.getenv('GOOGLE_API_KEY'),
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
            allowed_variables=allowed_vars,
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
            raise ValueError('Messages list cannot be empty.')

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

            print(msg)

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
                print(ev.data)
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

                runtime_builder.event('retrieval.started', {'query': ev.data.query})

                query_result_str = 'Vector storage is not configured.'
                results = []
                if self.__vector_storage:
                    rag_params = RAGParameters(
                        chunk_size=settings.rag_chunk_size,
                        chunk_overlap=settings.rag_chunk_overlap,
                        top_k=settings.rag_top_k,
                    )
                    results = self.__vector_storage.query(ev.data.query, rag_params)
                    query_result_str = format_query_results(results)

                runtime_builder.event('retrieval.completed', {'query': ev.data.query, 'chunks': results})

                thread.events.append(
                    AgentEvent(
                        type='query_documents_result',
                        data=QueryDocumentsResultEvent(query_result=query_result_str),
                    ),
                )

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

        if self.__runtime_state_repo:
            self.__runtime_state_repo.save(runtime)

        return MetricHelperResponse(
            response_text=response_text,
            metric_draft=metric_draft,
            runtime_id=runtime.runtime_id,
        )
