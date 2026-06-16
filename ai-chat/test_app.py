import os

from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

# Ensure the db folder exists
if not os.path.exists("db"):
    os.makedirs("db")

# Ensure dummy keys for SDK
os.environ["EVAL_API_KEY"] = "test_key"
os.environ["EVAL_BASE_URL"] = "http://localhost:8000"

from evalplatform_sdk.client import EvalClient
from evalplatform_sdk.helpers import trace
from parser import ingest_file
from rag_engine import generate_answer, retrieve_context

# Initialize client to prevent crash in decorators
client = EvalClient(api_key="test", base_url="http://test")

def main() -> None:
    print("Testing Ingestion...")
    # Create a dummy text file
    with open("dummy.txt", "w") as f:
        f.write("The quick brown fox jumps over the lazy dog. The AI Chat application was built in 2026.")

    try:
        chunks_count = ingest_file("dummy.txt")
        print(f"Ingested {chunks_count} chunks.")

        with trace() as state:
            print("Querying ChromaDB...")
            query = "When was the AI Chat application built?"
            context, image_paths = retrieve_context(state, query)
            print(f"Retrieved context:\n{context}")

            # Note: We won't test Gemini API call to save API tokens unless a valid key is provided
            # Or we can just mock it if we don't have the key
            print("To test generate_answer, ensure GEMINI_API_KEY is set in environment.")
            if "GEMINI_API_KEY" in os.environ:
                answer = generate_answer(state, query)
                print(f"Answer: {answer}")

        print("Test completed successfully.")
    finally:
        if os.path.exists("dummy.txt"):
            os.unlink("dummy.txt")

if __name__ == "__main__":
    main()
