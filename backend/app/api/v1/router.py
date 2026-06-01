"""API v1 master router."""

from app.api.v1.endpoints import agent, configs, documents, evals, events, runtimes
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(configs.router, prefix="/configs", tags=["configs"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(evals.router, prefix="/evaluations", tags=["evaluations"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(runtimes.router, prefix="/runtimes", tags=["runtimes"])
