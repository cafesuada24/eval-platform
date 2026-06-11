"""Module for generating text embeddings using Google GenAI."""

from functools import lru_cache
import time

from google import genai
from google.genai import types


@lru_cache(maxsize=1024)
def _cached_generate_embeddings(texts_tuple: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
    """Internal helper to batch and embed contents, cached via lru_cache."""
    if not texts_tuple:
        return ()

    client = genai.Client()
    max_retries = 3
    batch_size = 100
    all_embeddings = []

    for i in range(0, len(texts_tuple), batch_size):
        batch_texts = texts_tuple[i : i + batch_size]
        delay = 1
        for attempt in range(max_retries + 1):
            try:
                contents = [
                    types.Content(parts=[types.Part.from_text(text=t)])
                    for t in batch_texts
                ]
                response = client.models.embed_content(
                    model='gemini-embedding-2',
                    contents=contents,
                )
                embeddings = response.embeddings
                if not embeddings:
                    raise ValueError("Failed to retrieve embeddings from API response.")
                
                batch_vals = [
                    tuple(embedding.values)
                    for embedding in embeddings
                    if embedding.values is not None
                ]
                
                if len(batch_vals) != len(batch_texts):
                    raise ValueError(f"Mismatch in returned embeddings count. Expected {len(batch_texts)}, got {len(batch_vals)}")
                
                all_embeddings.extend(batch_vals)
                break
            except Exception as e:
                if attempt == max_retries:
                    raise e from e
                time.sleep(delay)
                delay *= 2

    return tuple(all_embeddings)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generates embedding vectors for a list of texts using gemini-embedding-2.

    Handles empty input lists, and implements exponential backoff retry logic
    for handling transient errors and rate limits.
    """
    res = _cached_generate_embeddings(tuple(texts))
    return [list(emb) for emb in res]
