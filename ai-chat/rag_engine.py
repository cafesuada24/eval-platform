"""RAG Engine and Context Hydration Module."""

import logging
import mimetypes
import time
from typing import Any

from embedder import generate_embeddings
from evalplatform_sdk.models import GenerationTracker, RuntimeState
from google import genai
from google.genai import types
from vector_store import query_vector_store

logger = logging.getLogger(__name__)

# Constants
MODEL_NAME = "gemini-3.1-flash-lite"
MAX_RETRIES = 3
INITIAL_DELAY = 1.0


def retrieve_context(state: RuntimeState, query: str, n_results: int = 3) -> tuple[str, list[str]]:
    """Retrieves relevant text context and associated image paths from vector store.

    Tracks execution using state retrieval context manager.
    """
    with state.track_retrieval() as rt:
        rt.query(query)

        embeddings = generate_embeddings([query])
        if not embeddings:
            return "", []

        query_vector = embeddings[0]
        results = query_vector_store(query_vector, n_results)
        if not results:
            return "", []

        image_paths: list[str] = []
        docs = results.get("documents", [[]])[0] if results.get("documents") else []
        metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
        distances = results.get("distances", [[]])[0] if results.get("distances") else []

        for i, doc in enumerate(docs):
            meta = metadatas[i] if i < len(metadatas) and metadatas[i] is not None else {}
            dist = distances[i] if i < len(distances) and distances[i] is not None else 1.0

            rt.add_chunk(
                document=str(meta.get("source_file", "")),
                content=doc,
                confidence=float(dist),
            )

            if meta.get("content_type") == "image_caption":
                asset_path = meta.get("asset_path")
                if asset_path:
                    image_paths.append(asset_path)

        joined_text = "\n\n".join(docs)
        return joined_text, image_paths


def generate_answer(state: RuntimeState, query: str, force_retrieve: bool = False) -> str:
    """Generates an answer using Gemini, with optional agentic retrieval.

    When force_retrieve=True (eval path): calls retrieve_context() unconditionally,
    then generates with context injected into the prompt.

    When force_retrieve=False (chat path): lets Gemini decide via Function Calling
    whether to call retrieve_documents. If it does, retrieve_context() is called
    and results injected; otherwise the model answers directly.

    Tracks LLM execution using state generation context manager.
    Handles transient errors with retries on all generate_content() calls.
    """
    client = genai.Client()

    with state.track_generation() as gen_tracker:
        gen_tracker.model_info(provider="google", model_name=MODEL_NAME)
        gen_tracker.user_input(query)

        if force_retrieve:
            answer = _generate_with_forced_retrieval(
                state, client, gen_tracker, MODEL_NAME, query
            )
        else:
            answer = _generate_agentic(
                state, client, gen_tracker, MODEL_NAME, query
            )

        gen_tracker.output_text(answer)
        return answer


def _call_generate_content_with_retry(
    client: genai.Client, **kwargs: Any
) -> types.GenerateContentResponse:
    """Calls client.models.generate_content with exponential backoff retry."""
    delay = INITIAL_DELAY
    for attempt in range(MAX_RETRIES + 1):
        try:
            return client.models.generate_content(**kwargs)
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise e
            time.sleep(delay)
            delay *= 2.0


def _generate_with_forced_retrieval(
    state: RuntimeState,
    client: genai.Client,
    gen_tracker: GenerationTracker,
    model_name: str,
    query: str,
) -> str:
    """Forced-retrieval path: always calls retrieve_context() before generation."""
    context, image_paths = retrieve_context(state, query)

    image_parts = _load_image_parts(image_paths)
    prompt_text = _build_rag_prompt(query, context)
    contents = [*image_parts, prompt_text]

    response = _call_generate_content_with_retry(
        client, model=model_name, contents=contents
    )

    _record_token_usage(gen_tracker, response)
    return response.text or ""


def _generate_agentic(
    state: RuntimeState,
    client: genai.Client,
    gen_tracker: GenerationTracker,
    model_name: str,
    query: str,
) -> str:
    """Agentic path: Gemini decides whether to call retrieve_documents tool."""
    retrieve_tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="retrieve_documents",
                description=(
                    "Search the document knowledge base for information relevant to "
                    "the user's question. Call this when the question requires factual "
                    "information from uploaded documents."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING,
                            description="The search query to run against the document store.",
                        )
                    },
                    required=["query"],
                ),
            )
        ]
    )

    system_instruction = (
        "You are a helpful AI assistant. "
        "If the user's question requires information from uploaded documents, "
        "call the retrieve_documents tool. "
        "If you can answer from your own knowledge, respond directly."
    )

    # First call: let the model decide
    response = _call_generate_content_with_retry(
        client,
        model=model_name,
        contents=query,
        tools=[retrieve_tool],
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )

    total_input_tokens = 0
    total_output_tokens = 0
    if response.usage_metadata:
        total_input_tokens += response.usage_metadata.prompt_token_count
        total_output_tokens += response.usage_metadata.candidates_token_count

    # Check if the model called the tool
    function_call = _extract_function_call(response)

    if function_call is None:
        # Model answered directly — no retrieval needed
        if total_input_tokens > 0 or total_output_tokens > 0:
            gen_tracker.token_usage(total_input_tokens, total_output_tokens)
        return response.text or ""

    # Model called retrieve_documents — execute it
    tool_query = function_call.get("query", query)
    if not isinstance(tool_query, str):
        logger.warning("retrieve_documents called with non-string query; using original query")
        tool_query = query

    context, image_paths = retrieve_context(state, tool_query)

    # Second call: send tool result back to model
    image_parts = _load_image_parts(image_paths)
    tool_result_part = types.Part.from_function_response(
        name="retrieve_documents",
        response={"context": context},
    )

    follow_up_contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=query)]),
        response.candidates[0].content,  # model's function_call turn
        types.Content(role="user", parts=[tool_result_part, *image_parts]),
    ]

    final_response = _call_generate_content_with_retry(
        client,
        model=model_name,
        contents=follow_up_contents,
        config=types.GenerateContentConfig(system_instruction=system_instruction),
    )

    if final_response.usage_metadata:
        total_input_tokens += final_response.usage_metadata.prompt_token_count
        total_output_tokens += final_response.usage_metadata.candidates_token_count

    if total_input_tokens > 0 or total_output_tokens > 0:
        gen_tracker.token_usage(total_input_tokens, total_output_tokens)
    return final_response.text or ""


def _extract_function_call(response: types.GenerateContentResponse) -> dict | None:
    """Extracts function call args from response, or returns None if not present."""
    try:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call:
                if part.function_call.name == "retrieve_documents":
                    return dict(part.function_call.args)
    except (AttributeError, IndexError, TypeError):
        pass
    return None


def _load_image_parts(image_paths: list[str]) -> list[types.Part]:
    """Loads image files as Part.from_bytes, skipping ones that fail."""
    parts = []
    for path in image_paths:
        try:
            mime_type, _ = mimetypes.guess_type(path)
            if not mime_type:
                mime_type = "image/jpeg"
            with open(path, "rb") as f:
                data = f.read()
            parts.append(
                types.Part.from_bytes(data=data, mime_type=mime_type)
            )
        except Exception as e:
            logger.error("Failed to load image part at %s: %s", path, e)
    return parts


def _build_rag_prompt(query: str, context: str) -> str:
    """Builds the RAG prompt string for forced-retrieval generation."""
    return (
        "You are a helpful AI assistant. Answer the user's question based ONLY on the provided context.\n"
        "If you cannot answer the question based on the context, say "
        '"I don\'t have enough information to answer that."\n\n'
        f"Context:\n{context}\n\nQuestion:\n{query}\n"
    )


def _record_token_usage(gen_tracker: GenerationTracker, response: types.GenerateContentResponse) -> None:
    """Records token usage telemetry if usage metadata is present."""
    if response.usage_metadata:
        gen_tracker.token_usage(
            input_tokens=response.usage_metadata.prompt_token_count,
            output_tokens=response.usage_metadata.candidates_token_count,
        )
