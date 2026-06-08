"""Application main entry."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from app.api.dependencies import get_metric_repo
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.eval_engine.models import Metric
from app.core.eval_engine.ports import MetricRepository
from app.core.exceptions import DomainError, NotFoundError
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter

load_dotenv()
logger = logging.getLogger(__name__)


def seed_default_metrics(repo: MetricRepository, default_metrics_dir: Path) -> None:
    """Seed default metrics from YAML files if not already present."""
    if not default_metrics_dir.exists():
        default_metrics_dir.mkdir(parents=True)
    if default_metrics_dir.is_file():
        raise ValueError('Default metric dir is not a directory.')
    adapter = TypeAdapter(Metric)
    for yaml_file in default_metrics_dir.glob('*.yaml'):
        try:
            with yaml_file.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    metric_name = data.get('name')
                    if metric_name:
                        existing = repo.find_by_name(metric_name)
                        if not existing:
                            logger.info(f'Seeding default metric: {metric_name}')
                            data['is_system_default'] = True
                            new_metric = adapter.validate_python(data)
                            repo.save(new_metric)
        except Exception as e:
            logger.error(f'Failed to seed metric from {yaml_file}: {e}')


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    # Startup: Seed default metrics
    repo = get_metric_repo()
    default_metrics_dir = settings.fixtures_dir / 'default_metrics'
    seed_default_metrics(repo, default_metrics_dir)
    yield


app = FastAPI(
    title='EvalPlatform Backend',
    description='The central ingestion, parsing, and execution engine for the EvalPlatform observability ecosystem.',
    version='0.1.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router, prefix='/v1')


@app.exception_handler(NotFoundError)
async def not_found_error_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={'detail': str(exc)},
    )


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    logger.warning(f'Domain error occurred: {str(exc)}')
    return JSONResponse(
        status_code=400,
        content={'detail': str(exc)},
    )


@app.get('/healthz')
async def healthz() -> dict[str, str]:
    return {'status': 'ok'}
