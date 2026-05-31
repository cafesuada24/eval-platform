from typing import Annotated
from uuid import UUID

from app.api.dependencies import get_metric_repo, get_pipeline_repo
from app.core.eval_engine.models import Metric, Pipeline
from app.core.eval_engine.ports import MetricRepository, PipelineRepository
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

# Metrics

@router.get("/metrics", response_model=list[Metric])
def list_metrics(
    metric_repo: Annotated[MetricRepository, Depends(get_metric_repo)],
) -> list[Metric]:
    return metric_repo.list_all()

@router.get("/metrics/{metric_id}", response_model=Metric)
def get_metric(
    metric_id: UUID,
    metric_repo: Annotated[MetricRepository, Depends(get_metric_repo)],
) -> Metric:
    metric = metric_repo.find_by_id(metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric

@router.post("/metrics", response_model=Metric, status_code=201)
def create_metric(
    metric: Metric,
    metric_repo: Annotated[MetricRepository, Depends(get_metric_repo)],
) -> Metric:
    if metric_repo.find_by_id(metric.id):
        raise HTTPException(status_code=409, detail="Metric already exists")
    metric_repo.save(metric)
    return metric

@router.put("/metrics/{metric_id}", response_model=Metric)
def update_metric(
    metric_id: UUID,
    metric: Metric,
    metric_repo: Annotated[MetricRepository, Depends(get_metric_repo)],
) -> Metric:
    if metric_id != metric.id:
        raise HTTPException(status_code=400, detail="ID in path must match payload")

    # Check if exists
    if not metric_repo.find_by_id(metric_id):
        raise HTTPException(status_code=404, detail="Metric not found")

    metric_repo.save(metric)
    return metric

# Pipelines

@router.get("/pipelines", response_model=list[Pipeline])
def list_pipelines(
    pipeline_repo: Annotated[PipelineRepository, Depends(get_pipeline_repo)],
) -> list[Pipeline]:
    return pipeline_repo.list_all()

@router.get("/pipelines/{pipeline_id}", response_model=Pipeline)
def get_pipeline(
    pipeline_id: UUID,
    pipeline_repo: Annotated[PipelineRepository, Depends(get_pipeline_repo)],
) -> Pipeline:
    pipeline = pipeline_repo.find_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline

@router.post("/pipelines", response_model=Pipeline, status_code=201)
def create_pipeline(
    pipeline: Pipeline,
    pipeline_repo: Annotated[PipelineRepository, Depends(get_pipeline_repo)],
) -> Pipeline:
    if pipeline_repo.find_by_id(pipeline.id):
        raise HTTPException(status_code=409, detail="Pipeline already exists")
    pipeline_repo.save(pipeline)
    return pipeline

@router.put("/pipelines/{pipeline_id}", response_model=Pipeline)
def update_pipeline(
    pipeline_id: UUID,
    pipeline: Pipeline,
    pipeline_repo: Annotated[PipelineRepository, Depends(get_pipeline_repo)],
) -> Pipeline:
    if pipeline_id != pipeline.id:
        raise HTTPException(status_code=400, detail="ID in path must match payload")

    if not pipeline_repo.find_by_id(pipeline_id):
        raise HTTPException(status_code=404, detail="Pipeline not found")

    pipeline_repo.save(pipeline)
    return pipeline
