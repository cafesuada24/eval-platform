"""Datasets endpoints."""

import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from app.api.dependencies import get_dataset_parser, get_dataset_repo
from app.api.v1.schemas.datasets import (
    DatasetCreate,
    DatasetUpdate,
    TestCaseCreate,
    TestCaseUpdate,
)
from app.core.config import settings
from app.core.eval_engine.models import Dataset, TestCase
from app.core.eval_engine.ports import DatasetRepository
from app.core.eval_engine.services.dataset_parser import (
    DatasetParserService,
    InvalidDatasetError,
)
from app.core.exceptions import NotFoundError
from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel


def get_dataset_files_dir() -> Path:
    """Lazily creates and returns the dataset files directory."""
    d = settings.dataset_files_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


router = APIRouter()


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    url: str


def _get_dataset_or_404(dataset_id: UUID, repo: DatasetRepository) -> Dataset:
    """Helper to fetch dataset and raise 404 if not found."""
    try:
        return repo.get_by_id(dataset_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail='Dataset not found') from e


@router.post('/upload', status_code=201)
async def upload_dataset(
    file: UploadFile,
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
    dataset_parser: Annotated[DatasetParserService, Depends(get_dataset_parser)],
    column_mapping: Annotated[str | None, Form()] = None,
    name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
) -> Dataset:
    """Upload a dataset (JSON, JSONL, or CSV)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail='Filename missing')

    parsed_mapping: dict[str, str] | None = None
    if column_mapping:
        try:
            parsed_mapping = json.loads(column_mapping)
            if not isinstance(parsed_mapping, dict):
                raise HTTPException(
                    status_code=400,
                    detail='column_mapping must be a JSON object',
                )
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f'Invalid JSON in column_mapping: {str(e)}',
            ) from e

    contents = await file.read()
    try:
        dataset = dataset_parser.parse(file.filename, contents, parsed_mapping)
    except InvalidDatasetError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if name:
        dataset.name = name
    if description is not None:
        dataset.description = description

    dataset_repo.save(dataset)
    return dataset


@router.post('/', status_code=201)
def create_dataset(
    data: DatasetCreate,
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
) -> Dataset:
    """Create an empty dataset."""
    dataset = Dataset(
        id=uuid4(),
        name=data.name,
        description=data.description,
        schema=data.schema_.model_dump(),
        cases=[],
    )
    dataset_repo.save(dataset)
    return dataset


@router.patch('/{dataset_id}')
def update_dataset(
    dataset_id: UUID,
    data: DatasetUpdate,
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
) -> Dataset:
    """Update dataset metadata."""
    dataset = _get_dataset_or_404(dataset_id, dataset_repo)
    if 'name' in data.model_fields_set and data.name is not None:
        dataset.name = data.name
    if 'description' in data.model_fields_set:
        dataset.description = data.description
    if 'schema_' in data.model_fields_set and data.schema_ is not None:
        dataset.schema = data.schema_.model_dump()
    dataset_repo.save(dataset)
    return dataset


@router.get('/')
def list_datasets(
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
) -> Sequence[Dataset]:
    """List datasets."""
    return dataset_repo.list_all()


@router.get('/{dataset_id}')
def get_dataset(
    dataset_id: UUID,
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
) -> Dataset:
    """Get a dataset by ID."""
    return _get_dataset_or_404(dataset_id, dataset_repo)


# --- FILES ---


@router.post('/{dataset_id}/files', status_code=201)
async def upload_dataset_file(
    dataset_id: UUID,
    file: UploadFile,
) -> FileUploadResponse:
    """Upload a file to be referenced in test cases."""
    if not file.filename:
        raise HTTPException(status_code=400, detail='Filename missing')

    dataset_dir = get_dataset_files_dir() / str(dataset_id)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    file_id = f'f_{uuid4().hex}'
    file_ext = Path(file.filename).suffix
    storage_name = f'{file_id}{file_ext}'
    file_path = dataset_dir / storage_name

    with file_path.open('wb') as buffer:
        shutil.copyfileobj(file.file, buffer)

    meta_path = dataset_dir / f'{storage_name}.meta.json'
    with meta_path.open('w') as f:
        json.dump({'original_filename': file.filename}, f)

    return FileUploadResponse(
        file_id=storage_name,
        filename=file.filename,
        url=f'/api/v1/datasets/{dataset_id}/files/{storage_name}',
    )


@router.get('/{dataset_id}/files')
def list_dataset_files(dataset_id: UUID) -> list[FileUploadResponse]:
    """List all files uploaded for a specific dataset."""
    dataset_dir = get_dataset_files_dir() / str(dataset_id)
    files: list[FileUploadResponse] = []

    if not dataset_dir.exists() or not dataset_dir.is_dir():
        return files

    for file_path in dataset_dir.iterdir():
        # Skip metadata files
        if file_path.is_file() and not file_path.name.endswith('.meta.json'):
            original_name = file_path.name
            meta_path = dataset_dir / f'{file_path.name}.meta.json'

            if meta_path.exists():
                try:
                    meta_data = json.loads(meta_path.read_text())
                    original_name = meta_data.get('original_filename', original_name)
                except json.JSONDecodeError:
                    pass

            files.append(
                FileUploadResponse(
                    file_id=file_path.name,
                    filename=original_name,
                    url=f'/api/v1/datasets/{dataset_id}/files/{file_path.name}',
                )
            )

    return files


@router.get('/{dataset_id}/files/{file_id}')
def get_dataset_file(dataset_id: UUID, file_id: str) -> FileResponse:
    """Retrieve a dataset file."""
    # Fallback to global directory for backwards compatibility with old uploads
    dataset_file_path = get_dataset_files_dir() / str(dataset_id) / file_id
    legacy_file_path = get_dataset_files_dir() / file_id

    if dataset_file_path.exists():
        return FileResponse(dataset_file_path)
    if legacy_file_path.exists():
        return FileResponse(legacy_file_path)

    raise HTTPException(status_code=404, detail='File not found')


@router.delete('/{dataset_id}/files/{file_id}', status_code=204)
def delete_dataset_file(dataset_id: UUID, file_id: str) -> None:
    """Delete a dataset file."""
    dataset_file_path = get_dataset_files_dir() / str(dataset_id) / file_id
    legacy_file_path = get_dataset_files_dir() / file_id

    if dataset_file_path.exists():
        dataset_file_path.unlink()
        # Clean up metadata file if it exists
        meta_path = dataset_file_path.with_name(f'{dataset_file_path.name}.meta.json')
        if meta_path.exists():
            meta_path.unlink()
    elif legacy_file_path.exists():
        legacy_file_path.unlink()


# --- TEST CASES ---


@router.post('/{dataset_id}/cases', status_code=201)
def create_test_case(
    dataset_id: UUID,
    data: TestCaseCreate,
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
) -> TestCase:
    """Add a test case to a dataset."""
    dataset = _get_dataset_or_404(dataset_id, dataset_repo)

    case = TestCase(
        id=uuid4(),
        inputs=data.inputs,
        expected_outputs=data.expected_outputs,
        metadata=data.metadata,
    )
    dataset.cases.append(case)
    dataset_repo.save(dataset)
    return case


@router.get('/{dataset_id}/cases')
def list_test_cases(
    dataset_id: UUID,
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
) -> Sequence[TestCase]:
    """List test cases for a dataset with pagination."""
    dataset = _get_dataset_or_404(dataset_id, dataset_repo)

    start = (page - 1) * limit
    end = start + limit
    return dataset.cases[start:end]


@router.put('/{dataset_id}/cases/{case_id}')
def update_test_case(
    dataset_id: UUID,
    case_id: UUID,
    data: TestCaseUpdate,
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
) -> TestCase:
    """Update a testcase inside a dataset."""
    dataset = _get_dataset_or_404(dataset_id, dataset_repo)

    for i, case in enumerate(dataset.cases):
        if case.id == case_id:
            updated_case = TestCase(
                id=case.id,
                inputs=data.inputs,
                expected_outputs=data.expected_outputs,
                metadata=data.metadata,
            )
            dataset.cases[i] = updated_case
            dataset_repo.save(dataset)
            return updated_case

    raise HTTPException(status_code=404, detail='Test case not found')


@router.delete('/{dataset_id}/cases/{case_id}', status_code=204)
def delete_test_case(
    dataset_id: UUID,
    case_id: UUID,
    dataset_repo: Annotated[DatasetRepository, Depends(get_dataset_repo)],
) -> None:
    """Delete a test case from a dataset."""
    dataset = _get_dataset_or_404(dataset_id, dataset_repo)

    original_length = len(dataset.cases)
    dataset.cases = [case for case in dataset.cases if case.id != case_id]

    if len(dataset.cases) == original_length:
        raise HTTPException(status_code=404, detail='Test case not found')

    dataset_repo.save(dataset)
