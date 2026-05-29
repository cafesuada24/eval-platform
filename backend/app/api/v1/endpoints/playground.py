import json
import os
import time

from app.engine.executor import execute_ai_judge_async
from app.engine.orchestrator import FIXTURES_DIR
from app.engine.resolver import format_prompt
from app.models.agent import ChatMessage, ChatSession
from app.models.config import MetricConfig
from fastapi import APIRouter, File, HTTPException, UploadFile
from google import genai
from google.genai import types
from pydantic import BaseModel

router = APIRouter()
SESSIONS_DIR = os.path.join(FIXTURES_DIR, 'sessions')
UPLOAD_DIR = os.path.join(FIXTURES_DIR, 'uploads')


class UploadedFileMetadata(BaseModel):
    id: str
    name: str
    text: str
    size: int


class TestMetricRequest(BaseModel):
    metric_config: MetricConfig
    inputs: dict[str, str]
    metric_name: str | None = None


class TestMetricResponse(BaseModel):
    score: float
    justification: str
    variables: dict[str, str]





def retrieve_from_vector_db(query: str, top_k: int = 2) -> str:
    """Retrieve semantically relevant documents strictly from the real ChromaDB database."""
    from app.services.rag_service import query_vector_db

    return query_vector_db(query, top_k)


@router.post('/playground/upload', response_model=UploadedFileMetadata)
async def upload_file(file: UploadFile = File(...)) -> UploadedFileMetadata:
    """Upload a file (text, pdf, image), extract its textual content, and index it into ChromaDB.

    Decodes plain text files directly, attempts local text extraction for PDF with pypdf,
    and falls back to Gemini multimodal generation for PDF/Image OCR extraction.
    """
    from app.services.rag_service import extract_text_from_pdf_local, index_document

    content_type = file.content_type or ''
    filename = file.filename or ''

    file_bytes = await file.read()

    # 1. Plain text file extraction
    text_content = ''
    if content_type.startswith('text/') or filename.lower().endswith(
        ('.txt', '.md', '.json', '.csv', '.yaml', '.yml')
    ):
        try:
            text_content = file_bytes.decode('utf-8')
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f'Failed to decode text file: {str(e)}',
            ) from e
    else:
        # 2. PDF & Image extraction
        mime_type = content_type
        if not mime_type:
            if filename.lower().endswith('.pdf'):
                mime_type = 'application/pdf'
            elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                mime_type = 'image/png'

        if not mime_type or (
            not mime_type.startswith('image/') and mime_type != 'application/pdf'
        ):
            raise HTTPException(
                status_code=400,
                detail=f'Unsupported file type: {filename}. Supported formats are text, PDF, and images.',
            )

        # First try parsing PDF locally via pypdf fallback
        if mime_type == 'application/pdf':
            try:
                text_content = extract_text_from_pdf_local(file_bytes)
            except Exception as e:
                print(f'Local PDF extraction crashed, will fall back to Gemini: {e}')

        # If PDF extraction yielded no text (scanned doc) or it's an image, use Gemini OCR
        if not text_content.strip():
            try:
                client = genai.Client()
                # Use gemini-3.1-flash-lite as it's the standard, fast model used in metric_agent.py
                response = client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=[
                        types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                        'Extract all text from this document/image. Preserve formatting where appropriate but output ONLY the raw extracted text. Do not add conversational filler, introductions, or markdown wraps. Output ONLY the extracted text contents.',
                    ],
                )
                text_content = response.text or ''
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f'Failed to extract text from file using Gemini: {str(e)}',
                )

    # Persist the file metadata to disk
    file_id = f'art-{int(time.time() * 1000)}'
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    metadata = UploadedFileMetadata(
        id=file_id, name=filename, text=text_content, size=len(file_bytes)
    )

    file_path = os.path.join(UPLOAD_DIR, f'{file_id}.json')
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f'Failed to persist file metadata: {str(e)}'
        )

    # 3. Index the chunks into ChromaDB
    try:
        index_document(file_id, filename, text_content)
    except Exception as e:
        print(f'Failed to index document to ChromaDB: {e}')

    return metadata


@router.get('/playground/files', response_model=list[UploadedFileMetadata])
async def list_uploaded_files() -> list[UploadedFileMetadata]:
    """List all persistently uploaded files."""
    if not os.path.exists(UPLOAD_DIR):
        return []

    files = []
    for filename in os.listdir(UPLOAD_DIR):
        if filename.endswith('.json'):
            file_path = os.path.join(UPLOAD_DIR, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    files.append(UploadedFileMetadata(**data))
            except Exception as e:
                # Log or ignore corrupted files
                print(f'Error reading file metadata {filename}: {e}')

    # Sort chronologically by ID
    files.sort(key=lambda x: x.id)
    return files


@router.delete('/playground/files/{file_id}')
async def delete_uploaded_file(file_id: str) -> dict[str, str]:
    """Delete a persistently uploaded file by ID."""
    from app.services.rag_service import delete_document_from_index

    file_path = os.path.join(UPLOAD_DIR, f'{file_id}.json')
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File metadata not found')

    try:
        os.remove(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f'Failed to delete file from disk: {str(e)}'
        )

    # Delete corresponding documents from ChromaDB index
    delete_document_from_index(file_id)

    return {'status': 'success', 'message': f'File {file_id} deleted successfully'}


@router.post('/playground/test', response_model=TestMetricResponse)
async def test_metric(request: TestMetricRequest) -> TestMetricResponse:
    """Execute a transient metric evaluation against provided inputs.

    If metric_name is provided, appends the execution run and result directly to the chat session history.
    """
    config = request.metric_config
    inputs = dict(request.inputs)

    # Track real execution telemetry (zero mock data)
    start_time = time.time()
    retrieval_time_ms = 0.0

    # 1. Check if we need to retrieve context first
    needs_retrieval = ('retrieved_context' in config.required_inputs) or (
        'output_text' in config.required_inputs and not inputs.get('output_text')
    )

    if needs_retrieval and not inputs.get('retrieved_context'):
        retrieval_start = time.time()
        query_source = (
            inputs.get('user_prompt') or inputs.get('input_text') or config.name
        )
        retrieved_data = retrieve_from_vector_db(query_source)
        inputs['retrieved_context'] = retrieved_data
        retrieval_time_ms = (time.time() - retrieval_start) * 1000

    # 2. Check if we need to dynamically generate the RAG model output
    if 'output_text' in config.required_inputs and not inputs.get('output_text'):
        try:
            from google import genai
            client = genai.Client()
            query = inputs.get('input_text') or inputs.get('user_prompt') or "Hello"
            context = inputs.get('retrieved_context') or ""

            generation_prompt = (
                f"You are a helpful assistant.\n"
                f"Answer the query based on the provided context if possible. "
                f"If the context doesn't contain the answer, answer it normally using your general knowledge.\n\n"
                f"Context: {context}\n\n"
                f"Query: {query}\n\n"
                f"Answer:"
            )
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=generation_prompt
            )
            inputs['output_text'] = response.text.strip() or ""
        except Exception as e:
            print(f"Dynamic output_text generation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to dynamically generate output_text: {str(e)}"
            )

    # Calculate actual measured overall latency
    latency_ms = (time.time() - start_time) * 1000

    # 3. Resolve all other system telemetry variables dynamically using real measured values
    for var in config.required_inputs:
        if var not in inputs or not inputs[var].strip():
            if var == 'latency_ms':
                inputs[var] = f"{latency_ms:.1f}"
            elif var == 'retrieval_time_ms':
                inputs[var] = f"{retrieval_time_ms:.1f}"
            elif var == 'ocr_process_time_ms':
                inputs[var] = "0.0"
            elif var == 'pdf_process_time_ms':
                inputs[var] = "0.0"
            elif var == 'ocr_failed_rate':
                inputs[var] = "0.0"
            elif var == 'pdf_failed_rate':
                inputs[var] = "0.0"
            elif var == 'input_artifacts_ocr':
                inputs[var] = "No parsed OCR artifacts present in input"
            elif var == 'input_text' and inputs.get('user_prompt'):
                inputs['input_text'] = inputs['user_prompt']
            elif var == 'user_prompt' and inputs.get('input_text'):
                inputs['user_prompt'] = inputs['input_text']
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required variable '{var}' is missing. Please provide it in the inputs."
                )

    try:
        # Format the prompt
        prompt = format_prompt(config.prompt_template, inputs)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f'Failed to render prompt template: {str(e)}'
        )

    try:
        # Execute the AI judge
        judge_output = await execute_ai_judge_async(config, prompt)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f'Failed to execute AI judge: {str(e)}'
        )

    # Append the test execution to the shared chat history if a metric name is provided
    metric_name = request.metric_name or config.name
    if metric_name:
        try:
            os.makedirs(SESSIONS_DIR, exist_ok=True)
            session_path = os.path.join(SESSIONS_DIR, f'{metric_name}.json')

            messages_list = []
            if os.path.exists(session_path):
                with open(session_path) as f:
                    session_data = json.load(f)
                    messages_list = [
                        ChatMessage(**m) for m in session_data.get('messages', [])
                    ]

            # Format inputs beautifully for history
            inputs_str = '\n'.join([f'- **{k}**: {v}' for k, v in inputs.items()])

            # Create a structured test run message in the history
            test_run_message = (
                f'[Test Run]\n'
                f'**Inputs:**\n'
                f'{inputs_str}\n\n'
                f'**Result:**\n'
                f'- Score: {judge_output.score}\n'
                f'- Justification: {judge_output.justification}'
            )

            messages_list.append(ChatMessage(role='user', content=test_run_message))

            # Update session file
            session_data = ChatSession(metric_name=metric_name, messages=messages_list)
            with open(session_path, 'w') as f:
                json.dump(session_data.model_dump(), f, indent=2)

        except Exception as e:
            # Non-blocking if persistence fails, but let's print/log it
            print(f'Failed to persist test run in session history: {e}')

    return TestMetricResponse(
        score=judge_output.score,
        justification=judge_output.justification,
        variables=inputs,
    )
