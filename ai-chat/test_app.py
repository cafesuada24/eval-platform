import os
import sys

# Ensure the db folder exists
if not os.path.exists("db"):
    os.makedirs("db")

# Ensure dummy keys for SDK
os.environ["EVAL_API_KEY"] = "test_key"
os.environ["EVAL_BASE_URL"] = "http://localhost:8000"

from ingest import ingest_file
from rag import add_chunks_to_db, retrieve_context, generate_answer
from evalplatform_sdk.client import EvalClient
from evalplatform_sdk.helpers import trace

# Initialize client to prevent crash in decorators
client = EvalClient(api_key="test", base_url="http://test")

def main():
    print("Testing Ingestion...")
    # Create a dummy text file
    with open("dummy.txt", "w") as f:
        f.write("The quick brown fox jumps over the lazy dog. The AI Chat application was built in 2026.")
    
    try:
        chunks = ingest_file("dummy.txt")
        print(f"Ingested {len(chunks)} chunks.")
        
        print("Adding to ChromaDB...")
        add_chunks_to_db(chunks, source="dummy.txt")
        
        with trace() as state:
            print("Querying ChromaDB...")
            query = "When was the AI Chat application built?"
            context = retrieve_context(state, query)
            print(f"Retrieved context:\n{context}")
            
            # Note: We won't test Gemini API call to save API tokens unless a valid key is provided
            # Or we can just mock it if we don't have the key
            print("To test generate_answer, ensure GEMINI_API_KEY is set in environment.")
            if "GEMINI_API_KEY" in os.environ:
                answer = generate_answer(state, query, context)
                print(f"Answer: {answer}")
        
        print("Test completed successfully.")
    finally:
        if os.path.exists("dummy.txt"):
            os.unlink("dummy.txt")

if __name__ == "__main__":
    main()
