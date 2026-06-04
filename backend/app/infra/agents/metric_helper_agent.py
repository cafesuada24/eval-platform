"""Agentic metric helper implementation."""

import os
import time
from string import Template

from app.core.agents.metric_helper.models import (
    AgentEvent,
    ChatMessage,
    ChatSession,
    MetricDraft,
    MetricHelperResponse,
    Thread,
)
from app.core.agents.metric_helper.utils import thread_to_prompt
from app.core.config import settings
from app.core.documents.ports import DocumentRepository
from app.core.eval_engine.extractors.runtime_state_extractor import (
    RuntimeStateExtractorService,
)
from app.core.kernel.builders.runtime_builder import RuntimeStateBuilder
from app.core.kernel.models import GenerationPayload, RetrievalPayload
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
        # Using 4 decimal places for score readability
        formatted.append(
            f'--- Document {i + 1} (Source: {doc_name}, Confidence Score: {res.score:.4f}) ---\n{res.document.text}\n',
        )
    return '\n'.join(formatted)


SYS_INSTRUCTION_TEMPLATE = Template(
    """<instruction>
You are an expert AI Metric Builder, who helps user build metrics based on their preference.
</instruction>

<allowed_variables>
$allowed_variables
</allowed_variables>

<rules>
1. Identify the user's intent to respond appropriately:
   - Normal Conversation: If the user simply says "Hi" or asks general questions (e.g., "What is a metric?"), set the `type` field to `"response"` and provide your conversational reply in the `response` field.
   - Testing/Querying: If the user asks questions about their uploaded documents, or explicitly wants to "test" a metric, set the `type` field to `"query_documents"` and put the query in the `query` field. When responding later, set `type` to `"response"` and provide your reply in the `response` field.
   - Creating/Updating a Metric: ONLY set the `type` field to `"create_or_update_metric"` when the user has provided clear requirements. Provide your conversational reply in the `response` field, and the draft in the `metric_draft` field.
2. For creating or updating metrics, you must autonomously decide which system variables are required.
3. You MUST select variables ONLY from the `allowed_variables` list. Do not invent variables.
4. Ensure `metric_draft` represents the complete draft configuration with all fields populated appropriately.
5. When generating the `prompt_template` for a metric, any variables you inject must be formatted using Jinja2 syntax (e.g., `{{ variable_name }}`). Do not use Python f-string formats like `{variable_name}`.
</rules>
""",
)


class GeminiMetricHelper:
    """Agentic builder backed by gemini."""

    def __init__(
        self,
        runtime_state_repo: RuntimeStateRepository | None = None,
        vector_storage: VectorStoragePort | None = None,
        document_repo: DocumentRepository | None = None,
        model: str = 'gemini-3.1-flash-lite',
    ) -> None:
        self.__model = model
        self.__runtime_state_repo = runtime_state_repo
        self.__vector_storage = vector_storage
        self.__document_repo = document_repo
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

        if self.__document_repo:
            docs = self.__document_repo.list_all()
            if docs:
                doc_list = '\n'.join([f'- {doc.name}' for doc in docs])
                system_instruction += f'\n\n<available_documents>\nThe user has uploaded the following files. If the user asks about them, their contents, or uses keywords relating to them, YOU MUST trigger the `query_documents` event with these filenames/keywords in mind.\n{doc_list}\n</available_documents>'

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

        formatted_contents: list[types.ContentDict] = [
            {
                'role': msg.role,
                'parts': [{'text': msg.content}],
            }
            for msg in messages
        ]

        thread = Thread(
            events=[
                AgentEvent(
                    type='user_message',
                    query=messages[-1].content,
                ),
            ],
        )

        original_user_input: str = messages[-1].content

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

            formatted_contents[-1] = {
                'role': 'user',
                'parts': [{'text': msg}],
            }

            response_time_start = time.perf_counter()
            response = await self.__client.aio.models.generate_content(
                model=self.__model,
                contents=formatted_contents,
                config=config,
            )
            response_time_fin = time.perf_counter()

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

            runtime_builder.event(
                GenerationPayload(
                    provider='google',
                    model=self.__model,
                    input_text=original_user_input,
                    prompt=msg,
                    output_text=ev.response or '',
                    latency_ms=int(
                        (response_time_fin - response_time_start) * 1000,
                    ),
                    input_tokens=response.usage_metadata.prompt_token_count or 0,
                    output_tokens=response.usage_metadata.candidates_token_count or 0,
                ),
            )

            if ev.type == 'response':
                assert ev.response is not None
                response_text = ev.response
                break

            if ev.type == 'create_or_update_metric':
                assert ev.response is not None
                response_text = ev.response
                metric_draft = ev.metric_draft
                break

            if ev.type == 'query_documents':
                assert ev.query is not None
                query_result_str = 'Vector storage is not configured.'
                results = []
                retrieval_latency_ms = 0
                if self.__vector_storage:
                    rag_params = RAGParameters(
                        chunk_size=settings.rag_chunk_size,
                        chunk_overlap=settings.rag_chunk_overlap,
                        top_k=settings.rag_top_k,
                    )
                    retrieval_start = time.perf_counter()
                    results = self.__vector_storage.query(ev.query, rag_params)
                    retrieval_latency_ms = int(
                        (time.perf_counter() - retrieval_start) * 1000,
                    )
                    query_result_str = format_query_results(results)

                thread.events.append(
                    AgentEvent(
                        type='query_documents_result',
                        query_result=query_result_str,
                    ),
                )

                runtime_builder.event(
                    RetrievalPayload(
                        query=ev.query,
                        chunks=[
                            {
                                'document': chunk.document.metadata.get('filename', chunk.document.id) or 'unknown',
                                'content': chunk.document.text,
                                'confidence': chunk.score,
                            } for chunk in results

                        ],
                        latency_ms=retrieval_latency_ms,
                    ),
                )

        delta = time.perf_counter() - start

        runtime_builder.token_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        runtime_builder.latency_ms(int(delta * 1000))
        runtime = runtime_builder.build()

        if self.__runtime_state_repo:
            self.__runtime_state_repo.save(runtime)

        return MetricHelperResponse(
            response_text=response_text,
            metric_draft=metric_draft,
            runtime_id=runtime.runtime_id,
        )
