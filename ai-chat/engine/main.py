import base64
import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from generator import generate_rag_response
from retriever import process_upload

app = FastAPI(title="EvalPlatform RAG API")

# Enable CORS for Next.js UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def format_vercel_ai_stream(generator):
    """
    Formats the text chunks into Vercel AI SDK Data Stream Protocol.
    0:"text content"\n
    """
    async for chunk in generator:
        if chunk:
            yield f'0:{json.dumps(chunk)}\n'

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    payload = await request.json()
    messages = payload.get("messages", [])
    attachments = payload.get("attachments", [])
    
    # Process files into ChromaDB
    for att in attachments:
        mime_type = att.get("type", "")
        b64_str = att.get("base64", "")
        name = att.get("name", "")
        
        if b64_str:
            if "," in b64_str:
                b64_str = b64_str.split(",")[1]
            try:
                file_bytes = base64.b64decode(b64_str)
                process_upload(file_bytes, mime_type, name)
            except Exception as e:
                print(f"Error processing attachment {name}: {e}")

    # Extract the latest user message
    user_message = ""
    if messages:
        user_message = messages[-1].get("content", "")
        
    # Call the generator which returns an async generator
    response_gen = generate_rag_response(user_message, attachments)
    
    # Return via StreamingResponse
    return StreamingResponse(
        format_vercel_ai_stream(response_gen),
        media_type="text/plain; charset=utf-8"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
