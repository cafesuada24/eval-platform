import os
import uuid

import chromadb
from evalplatform_sdk.models import RuntimeState
from google import genai

DB_DIR = os.path.join(os.path.dirname(__file__), 'db')
chroma_client = chromadb.PersistentClient(path=DB_DIR)
collection = chroma_client.get_or_create_collection(name='ai_chat_docs')


def add_chunks_to_db(chunks: list[str], source: str):
    """Adds a list of text chunks to ChromaDB."""
    if not chunks:
        return
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{'source': source} for _ in chunks]
    collection.add(documents=chunks, metadatas=metadatas, ids=ids)


def retrieve_context(state: RuntimeState, query: str, n_results: int = 3) -> str:
    """Retrieves relevant context from ChromaDB based on the query."""

    with state.track_retrieval() as rt:
        rt.query(query)

        if collection.count() == 0:
            return ''

        results = collection.query(
            query_texts=[query], n_results=min(n_results, collection.count())
        )

        if results and results.get('documents') and results['documents'][0]:
            docs = results['documents'][0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]

            for i in range(len(docs)):
                doc_metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                source = doc_metadata.get('source', '')
                distance = distances[i] if distances and i < len(distances) else 1.0
                rt.add_chunk(
                    document=source, content=docs[i], confidence=float(distance)
                )

            context = '\n\n'.join(docs)
        else:
            context = ''

        return context


def generate_answer(state: RuntimeState, query: str, context: str) -> str:
    """Generates an answer using Gemini based on the query and context."""

    model_name = 'gemini-3.1-flash-lite'
    client = genai.Client()

    prompt = f"""You are a helpful AI assistant. Answer the user's question based ONLY on the provided context.
If you cannot answer the question based on the context, say "I don't have enough information to answer that."

Context:
{context}

Question:
{query}
"""

    with state.track_generation() as gen_tracker:
        gen_tracker.model_info(provider='google', model_name=model_name)
        gen_tracker.user_input(query)

        response = client.models.generate_content(model=model_name, contents=prompt)
        answer = response.text

        if response.usage_metadata:
            gen_tracker.token_usage(
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count,
            )
        gen_tracker.output_text(answer or '')

    return answer
