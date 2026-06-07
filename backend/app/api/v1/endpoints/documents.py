from typing import Annotated

from app.api.dependencies import get_document_service
from app.api.v1.schemas.documents_dtos import UploadedFileMetadata
from app.core.documents.services import DocumentService
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from google import genai
from google.genai import types

router = APIRouter()


@router.post('/upload')
async def upload_file(
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    file: UploadFile,
) -> UploadedFileMetadata:
    """Upload a file (text, pdf, image), extract its textual content via Gemini, and save as a document."""
    content_type = file.content_type or ''
    filename = file.filename or ''

    file_bytes = await file.read()

    # 1. Plain text file extraction
    text_content = ''
    if content_type.startswith('text/') or filename.lower().endswith(
        ('.txt', '.md', '.json', '.csv', '.yaml', '.yml'),
    ):
        try:
            text_content = file_bytes.decode('utf-8')
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f'Failed to decode text file: {str(e)}',
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

        # Use Gemini OCR to extract text from PDF and images
        if not text_content.strip():
            try:
                client = genai.Client()
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
                ) from e

    try:
        metadata = document_service.save_and_index_document(
            filename=filename,
            text_content=text_content,
            size=len(file_bytes),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f'Failed to save and index document: {str(e)}',
        ) from e

    # Return DTO
    return UploadedFileMetadata(**metadata.model_dump())


@router.get('')
async def list_uploaded_files(
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> list[UploadedFileMetadata]:
    """List all persistently uploaded files."""
    docs = document_service.list_documents()

    # Map to DTOs
    files = [UploadedFileMetadata(**doc.model_dump()) for doc in docs]
    files.sort(key=lambda x: x.id)
    return files


@router.delete('/{file_id}', status_code=204)
async def delete_uploaded_file(
    file_id: str,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> None:
    """Delete a persistently uploaded file by ID."""
    doc = document_service.get_document(file_id)
    if not doc:
        raise HTTPException(status_code=404, detail='File metadata not found')

    try:
        document_service.delete_document(file_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f'Failed to delete file from disk and vector storage: {str(e)}',
        ) from e

