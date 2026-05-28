import os
import yaml
from fastapi import APIRouter, HTTPException
from typing import List

from app.models.config import MetricConfig, PipelineConfig
from app.engine.orchestrator import FIXTURES_DIR, load_metric_config, load_pipeline_config

router = APIRouter()

METRICS_DIR = os.path.join(FIXTURES_DIR, 'metrics')
PIPELINES_DIR = os.path.join(FIXTURES_DIR, 'pipelines')

@router.get("/metrics", response_model=List[MetricConfig])
def list_metrics():
    metrics = []
    if os.path.exists(METRICS_DIR):
        for entry in os.listdir(METRICS_DIR):
            if entry.endswith(('.yaml', '.yml')):
                path = os.path.join(METRICS_DIR, entry)
                with open(path) as f:
                    data = yaml.safe_load(f)
                    if data:
                        metrics.append(MetricConfig(**data))
    return metrics

@router.get("/metrics/{name}", response_model=MetricConfig)
def get_metric(name: str):
    try:
        return load_metric_config(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Metric not found")

@router.post("/metrics", response_model=MetricConfig)
@router.put("/metrics/{name}", response_model=MetricConfig)
def save_metric(metric: MetricConfig, name: str | None = None):
    if name and name != metric.name:
        raise HTTPException(status_code=400, detail="Name in path does not match metric name")
    
    os.makedirs(METRICS_DIR, exist_ok=True)
    path = os.path.join(METRICS_DIR, f"{metric.name}.yaml")
    
    with open(path, "w") as f:
        yaml.dump(metric.model_dump(exclude_unset=True), f, sort_keys=False)
    
    return metric

@router.get("/pipelines", response_model=List[PipelineConfig])
def list_pipelines():
    pipelines = []
    if os.path.exists(PIPELINES_DIR):
        for entry in os.listdir(PIPELINES_DIR):
            if entry.endswith(('.yaml', '.yml')):
                path = os.path.join(PIPELINES_DIR, entry)
                with open(path) as f:
                    data = yaml.safe_load(f)
                    if data:
                        pipelines.append(PipelineConfig(**data))
    return pipelines

@router.get("/pipelines/{name}", response_model=PipelineConfig)
def get_pipeline(name: str):
    try:
        return load_pipeline_config(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pipeline not found")

@router.post("/pipelines", response_model=PipelineConfig)
@router.put("/pipelines/{name}", response_model=PipelineConfig)
def save_pipeline(pipeline: PipelineConfig, name: str | None = None):
    if name and name != pipeline.name:
        raise HTTPException(status_code=400, detail="Name in path does not match pipeline name")
        
    os.makedirs(PIPELINES_DIR, exist_ok=True)
    path = os.path.join(PIPELINES_DIR, f"{pipeline.name}.yaml")
    
    with open(path, "w") as f:
        yaml.dump(pipeline.model_dump(exclude_unset=True), f, sort_keys=False)
        
    return pipeline
