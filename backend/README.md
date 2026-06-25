# EvalPlatform Backend

The backend is the central ingestion, parsing, and execution engine for the EvalPlatform observability and telemetry ecosystem. It provides FastAPIs for capturing telemetry traces, managing datasets, evaluating models against metrics, and tracking runs.

---

## Architecture & Layout

The project follows a clean, decoupled layout:

```plaintext
backend/
├── app/
│   ├── api/                  # API routers, endpoints, and schemas
│   ├── core/                 # Config, Domain models, and evaluation kernel logic
│   ├── infra/                # Repository and storage implementations
│   └── main.py               # Fast API application entry and lifespan setup
├── fixtures/                 # Default persistence folder (Gitignored bind mount target)
└── tests/                    # Unit and integration test suite
```

### In-Memory / File-based Persistence

To avoid database setup overhead, the backend uses a file-based repository model (`app/infra/repositories/`). Data is stored as JSON/YAML files under the `fixtures/` directory:

* **Runtimes & Traces:** Saved as YAML under `fixtures/runtimes/`
* **Metrics:** Saved as YAML under `fixtures/metrics/`
* **Pipelines:** Saved as YAML under `fixtures/pipelines/`
* **Datasets & Documents:** Saved as JSON under `fixtures/datasets/` and `fixtures/documents/`

---

## API Endpoints

Once running, interactive Swagger documentation is available at `http://localhost:8000/docs`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/runtimes` | `PUT` / `POST` / `GET` | Ingest single/batch telemetry traces, list and view traces. |
| `/v1/datasets` | `POST` / `GET` / `DELETE` | Upload datasets, upload file rows, list and manage test datasets. |
| `/v1/evaluations` | `POST` / `GET` | Run pipeline evaluations and score results. |
| `/v1/documents` | `POST` / `GET` | Ingest and index documents in ChromaDB vector store. |
| `/v1/configs` | `GET` / `PUT` | Read and configure runtime hyperparameters (e.g. chunk size). |
| `/v1/agent` | `POST` | Interact with agent runners. |
| `/healthz` | `GET` | Direct endpoint for orchestrator and Docker health checks. |

---

## Local Development

### Prerequisites

* Python 3.12+
* [uv](https://github.com/astral-sh/uv) (recommended package manager)

### 1. Sync Dependencies
Install backend dependencies and register the editable `sdk/` package:
```bash
# Run from repository root
uv sync
```

### 2. Configure Environment
Create a `.env` file in the `backend/` directory:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 3. Launch Development Server
```bash
# Run from repository root
uv run uvicorn app.main:app --reload --port 8000
```
API server will start on [http://localhost:8000](http://localhost:8000).

---

## Testing

Run pytest suite locally to verify endpoint handlers and models:
```bash
# Run from repository root
uv run pytest backend/
```
