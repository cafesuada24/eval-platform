from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import events, configs, agent, playground

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="EvalPlatform Backend",
    description="The central ingestion, parsing, and execution engine for the EvalPlatform observability ecosystem.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the routers
app.include_router(events.router, prefix="/v1", tags=["events"])
app.include_router(configs.router, prefix="/v1", tags=["configs"])
app.include_router(agent.router, prefix="/v1/agent", tags=["agent"])
app.include_router(playground.router, prefix="/v1", tags=["playground"])

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

