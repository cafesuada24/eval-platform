from fastapi import FastAPI
from app.api.routes import events, configs, agent

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="EvalPlatform Backend",
    description="The central ingestion, parsing, and execution engine for the EvalPlatform observability ecosystem.",
    version="0.1.0"
)

# Include the routers
app.include_router(events.router, prefix="/v1", tags=["events"])
app.include_router(configs.router, prefix="/v1", tags=["configs"])
app.include_router(agent.router, prefix="/v1/agent", tags=["agent"])

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
