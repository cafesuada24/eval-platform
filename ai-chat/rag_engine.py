"""RAG Engine and Context Hydration Module."""

import logging
import time

from embedder import generate_embeddings
from evalplatform_sdk.models import RuntimeState
from google import genai
from PIL import Image
from vector_store import query_vector_store

logger = logging.getLogger(__name__)


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


def generate_answer(state: RuntimeState, query: str, context: str, image_paths: list[str]) -> str:
    """Generates a multimodal answer using Gemini based on query, context and hydrated images.

    Tracks LLM execution using state generation context manager and handles transient errors with retries.
    """
    model_name = "gemini-3.1-flash-lite"

    with state.track_generation() as gen_tracker:
        gen_tracker.model_info(provider="google", model_name=model_name)
        gen_tracker.user_input(query)

        loaded_images = []
        for path in image_paths:
            try:
                img = Image.open(path)
                loaded_images.append(img)
            except Exception as e:
                logger.error("Failed to open image at %s: %s", path, e)

        prompt_text = f"""You are a helpful AI assistant. Answer the user's question based ONLY on the provided context.
If you cannot answer the question based on the context, say "I don't have enough information to answer that."

Context:
{context}

Question:
{query}
"""

        contents = [*loaded_images, prompt_text]
        client = genai.Client()

        max_retries = 3
        delay = 1.0
        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,  # type: ignore[arg-type]
                )
                break
            except Exception as e:
                if attempt == max_retries:
                    raise e
                time.sleep(delay)
                delay *= 2.0

        answer = response.text or ""

        if response.usage_metadata:
            gen_tracker.token_usage(
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
            )

        gen_tracker.output_text(answer)
        return answer
