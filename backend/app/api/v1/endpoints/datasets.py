"""Datasets endpoints."""

from uuid import UUID

from app.api.dependencies import get_dataset_parser, get_dataset_repo
from app.core.eval_engine.models import Dataset
from app.core.eval_engine.ports import DatasetRepository
from app.core.eval_engine.services.dataset_parser import (
    DatasetParserService,
    InvalidDatasetError,
)
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

router = APIRouter()


@router.post("/", response_model=Dataset, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_repo: DatasetRepository = Depends(get_dataset_repo),
    dataset_parser: DatasetParserService = Depends(get_dataset_parser),
) -> Dataset:
    """Upload a dataset (JSON or CSV)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    contents = await file.read()
    try:
        dataset = dataset_parser.parse(file.filename, contents)
    except InvalidDatasetError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dataset_repo.save(dataset)
    return dataset


@router.get("/", response_model=list[Dataset])
def list_datasets(
    dataset_repo: DatasetRepository = Depends(get_dataset_repo),
) -> list[Dataset]:
    """List datasets."""
    return dataset_repo.list_all()


@router.get("/{dataset_id}", response_model=Dataset)
def get_dataset(
    dataset_id: UUID,
    dataset_repo: DatasetRepository = Depends(get_dataset_repo),
) -> Dataset:
    """Get a dataset by ID."""
    try:
        return dataset_repo.get_by_id(dataset_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Dataset not found") from e
