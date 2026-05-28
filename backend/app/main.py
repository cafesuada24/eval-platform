from fastapi import FastAPI
from app.api.routes import events

app = FastAPI(
    title="EvalPlatform Backend",
    description="The central ingestion, parsing, and execution engine for the EvalPlatform observability ecosystem.",
    version="0.1.0"
)

# Include the routers
app.include_router(events.router, prefix="/v1", tags=["events"])

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
