import logging
from contextlib import asynccontextmanager

import yaml
from app.api.dependencies import get_metric_repo
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.eval_engine.models import Metric
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import TypeAdapter
from app.core.exceptions import DomainError, NotFoundError

load_dotenv()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed default metrics
    repo = get_metric_repo()
    default_metrics_dir = settings.fixtures_dir / 'default_metrics'
    if default_metrics_dir.exists():
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
                                logger.info(f"Seeding default metric: {metric_name}")
                                data['is_system_default'] = True
                                new_metric = adapter.validate_python(data)
                                repo.save(new_metric)
            except Exception as e:
                logger.error(f"Failed to seed metric from {yaml_file}: {e}")
    yield

app = FastAPI(
    title="EvalPlatform Backend",
    description="The central ingestion, parsing, and execution engine for the EvalPlatform observability ecosystem.",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/v1")

@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )

@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    logger.warning(f"Domain error occurred: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

