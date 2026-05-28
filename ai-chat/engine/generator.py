import uuid
import base64
from typing import List, Dict, Any, AsyncGenerator

from evalplatform_sdk.helpers import trace
from evalplatform_sdk.models import Artifact
from google import genai
from google.genai import types

from retriever import retrieve_context

# Initialize Gemini Client
# It assumes GEMINI_API_KEY is available in the environment
try:
    client = genai.Client()
except Exception as e:
    print(f"Warning: Could not initialize Gemini client: {e}")
    client = None

async def generate_rag_response(user_message: str, files: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    """
    Generate a response using Gemini, wrapped in evalplatform_sdk telemetry.
    `files` is a list of dicts with 'name', 'type', and 'base64'.
    """
    trace_id = str(uuid.uuid4())
    
    with trace(trace_id=trace_id) as t:
        # 1. Retrieve Context
        retrieved_chunks = retrieve_context(user_message)
        
        # 2. Package SDK Metadata (CRITICAL for the Backend Extractor)
        t.set_metadata({"retrieved_context": retrieved_chunks})
        
        # 3. Package Artifacts
        contents = []
        for file in files:
            t.add_artifact(Artifact(type=file.get('type', 'application/octet-stream'), content=file.get('base64', '')))
            
            # Prepare multimodal content for Gemini
            if file.get('base64'):
                # Extract the base64 part if it's a data URL
                b64_str = file['base64']
                if "," in b64_str:
                    b64_str = b64_str.split(",")[1]
                
                try:
                    file_bytes = base64.b64decode(b64_str)
                    contents.append(
                        types.Part.from_bytes(
                            data=file_bytes,
                            mime_type=file.get('type', 'application/octet-stream')
                        )
                    )
                except Exception as e:
                    print(f"Error decoding base64 file {file.get('name')}: {e}")
        
        # 4. Construct Prompt
        context_str = "\n".join(retrieved_chunks) if retrieved_chunks else "No retrieved context available."
        system_instruction = f"Answer the user's question based on the following context.\n\nContext:\n{context_str}"
        
        contents.append(user_message)
        
        # Yield the response incrementally while building the full text for telemetry
        full_response = ""
        
        if not client:
            error_msg = "Gemini API client is not initialized. Please check your GEMINI_API_KEY."
            yield error_msg
            full_response = error_msg
            t.set_input(user_message)
            t.set_output(full_response)
            return

        try:
            # We use gemini-2.5-flash as the fast multimodal model
            response_stream = client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )
            
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    yield chunk.text
        except Exception as e:
            error_msg = f"\nError calling Gemini: {e}"
            yield error_msg
            full_response += error_msg

        # 5. Finalize Trace
        t.set_input(user_message)
        t.set_output(full_response)
