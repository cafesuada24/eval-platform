from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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
from app.api.v1.router import api_router

app.include_router(api_router, prefix="/v1")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

