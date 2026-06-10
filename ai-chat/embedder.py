"""Module for generating text embeddings using Google GenAI."""

import time

from google import genai


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generates embedding vectors for a list of texts using gemini-embedding-2.

    Handles empty input lists, and implements exponential backoff retry logic
    for handling transient errors and rate limits.
    """
    if not texts:
        return []

    client = genai.Client()
    max_retries = 3
    delay = 1

    for attempt in range(max_retries + 1):
        try:
            response = client.models.embed_content(
                model='gemini-embedding-2',
                contents=texts,
            )
            return [embedding.values for embedding in response.embeddings]
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(delay)
            delay *= 2

    raise RuntimeError('Unreachable')
