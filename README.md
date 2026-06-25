# EvalPlatform

EvalPlatform is a modular, context-driven observability and telemetry ingestion engine designed to track, benchmark, and evaluate LLM and Retrieval-Augmented Generation (RAG) applications. It provides real-time telemetry tracing, structured RAG metrics analysis, automated batch evaluation pipelines, and a unified Next.js dashboard.

---

## Repository Architecture

This repository is organized as a monorepo containing the following components:

```plaintext
eval-platform/
├── backend/                  # FastAPI telemetry ingestion & execution engine
├── frontend/                 # Next.js 16 Web Dashboard and metrics UI
├── sdk/                      # Context-driven Python Telemetry SDK (evalplatform-sdk)
├── ai-chat/                  # Multimodal RAG pipeline & evaluation playground
└── data/fixtures/            # Bind mount for persistent telemetry database (ChromaDB)
```

| Component | Role | Technologies | Detailed Docs |
|---|---|---|---|
| **[Backend](./backend/)** | Central API ingestion, session tracking, and evaluations processor. | Python 3.12, FastAPI, Uvicorn, ChromaDB | [Backend Guide](./backend/README.md) |
| **[Frontend](./frontend/)** | Interactive metrics UI, performance dashboard, and trace viewer. | React 19, Next.js 16 (standalone), Tailwind CSS v4 | [Frontend README](./frontend/README.md) |
| **[SDK](./sdk/)** | Async context-manager-driven telemetry tracker for Python apps. | Python, ThreadPoolExecutor telemetry worker | [SDK Guide](./sdk/README.md) |
| **[AI Chat](./ai-chat/)** | Document parsing (PDF visual OCR) and Gemini RAG benchmarking suite. | Google GenAI SDK, ChromaDB, PyMuPDF | [AI Chat README](./ai-chat/README.md) |

---

## Core Ingestion Concepts

EvalPlatform structures telemetry collection into four distinct layers:

1. **Traces:** Context managers (`trace()`) capture execution boundaries, tracking end-to-end latency, and token usage asynchronously.
2. **File Processing:** Tracks parsing and OCR events (e.g. converting scanned PDFs/images to structured markdown chunks).
3. **Retrievals:** Logs RAG queries and retrieved document chunks, including content and confidence scores.
4. **Generations:** Records prompts, responses, model names, providers, and exact token usages.
5. **Evaluations:** Aggregates traces against reference datasets using LLM-as-a-judge pipelines to verify system output quality.

---

## Quick Start (Docker Compose)

The entire platform is containerized using multi-stage Dockerfiles. A base-plus-override model is used to manage different environments.

### Prerequisites

- [Docker](https://docs.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
- A Google Gemini API key (for RAG parsing and LLM operations)

### 1. Configure the Environment

Copy the environment template to `.env` at the root of the repository:
```bash
cp .env.example .env
```

Edit the `.env` file and fill in your keys:
```env
GOOGLE_API_KEY=AIzaSy...
CLOUDFLARE_TUNNEL_TOKEN=ey... # Optional: Only required for production ingress
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Run in Development Mode
Binds the services to local ports for easy code testing and hot-reloading:
```bash
docker compose up --build -d
```
- **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
- **Backend API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/healthz](http://localhost:8000/healthz)

### 3. Run in Production Mode
Strips host port exposures (port 3000 and 8000) for security, enforces CPU/memory resource limits, and routes ingress traffic exclusively via a Cloudflare Tunnel:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

### 4. Run AI Chat & Benchmark Jobs
The `ai-chat` container is run on-demand using Docker Compose profiles:
```bash
# Run interactive RAG terminal interface
docker compose --profile tools run ai-chat python main.py

# Run RAG evaluation benchmark suite
docker compose --profile tools run ai-chat python benchmark.py
```

---

## Local Development Setup

To run services natively outside of containers:

### Backend & SDK Setup

The project uses `uv` as the workspace package manager:
```bash
# Sync and install all workspace packages
uv sync

# Run backend development server
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm ci
npm run dev
```

---

## Testing & Quality

To run validation checks across the workspace:

### Running Test Suites

```bash
# Run backend & SDK unit tests
cd backend && uv run pytest

# Run AI-Chat RAG tests
cd ai-chat && uv run pytest
```

### Running Validation Scripts
The repository includes automated master validation scripts inside the `.agents/` directory:

```bash
# Run core quality audit (Security scan, lint checks, schema verification)
python .agents/scripts/checklist.py .

# Run full pre-deployment suite (E2E Playwright, Lighthouse profiling, UX check)
python .agents/scripts/verify_all.py . --url http://localhost:3000
```

---

## 📝 Configuration & Environment Variables

| Variable | Scope | Description | Default |
|---|---|---|---|
| `GOOGLE_API_KEY` | Backend, AI Chat | Gemini API Authentication Key | None (Required) |
| `CLOUDFLARE_TUNNEL_TOKEN` | Tunnel | Ingress token for Cloudflare Tunnel | None (Optional) |
| `NEXT_PUBLIC_API_URL` | Frontend | Target API server URL for Next.js app | `http://localhost:8000` |

---

## License

This project is licensed under the MIT License.
