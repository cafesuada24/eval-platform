# Docker Compose Deployment Design

**Date:** 2026-06-25
**Status:** Approved
**Scope:** Dockerize the eval-platform monorepo for cloud VM deployment with Cloudflare Tunnel

---

## Overview

Containerize the eval-platform monorepo using Docker Compose with a base + production override pattern. All three services (backend, frontend, ai-chat) get multi-stage Dockerfiles. External traffic is routed entirely through a Cloudflare Tunnel — no ports exposed to the host in production.

---

## Architecture

### Services

| Service | Image | Role | Long-running? |
|---|---|---|---|
| `backend` | custom Python 3.12 | FastAPI + uvicorn on port 8000 | Yes |
| `frontend` | custom Node 22 | Next.js standalone on port 3000 | Yes |
| `ai-chat` | custom Python 3.12 | On-demand batch runner | No (profiles: tools) |
| `tunnel` | `cloudflare/cloudflared:latest` | Routes external HTTPS traffic in | Yes |

### Network & Traffic Flow

```
Internet
   │
   ▼
Cloudflare Edge (HTTPS)
   │
   ▼
cloudflared container (token-only mode)
   │
   ├──► frontend:3000    (app.yourdomain.com)
   └──► backend:8000     (api.yourdomain.com)

Internal bridge network: eval-net
No host ports exposed in production.
```

### Persistence

```
Host: ./data/fixtures/
   └──► backend container at /app/fixtures
        Covers: ChromaDB data, YAML fixtures, uploads, sessions,
                datasets, batch results, prompts
```

---

## Dockerfiles

### Backend (`backend/Dockerfile`)

Multi-stage. Build context is the **monorepo root** (required because the `sdk/` workspace package must be present during `uv sync`).

| Stage | Base image | Purpose |
|---|---|---|
| `builder` | `python:3.12-slim` | Install uv, run `uv sync --frozen --no-dev` with workspace deps |
| `runtime` | `python:3.12-slim` | Copy `.venv` + app code only; run as non-root `appuser` |

Key decisions:
- Build context is `./` (monorepo root) so `sdk/` and `uv.lock` are available
- `--frozen` ensures the lockfile is respected (reproducible builds)
- `--no-dev` excludes pytest and other dev tools from the image
- `HEALTHCHECK` hits `GET /healthz`
- `CMD`: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1`

### Frontend (`frontend/Dockerfile`)

Multi-stage using Next.js **standalone output** mode.

| Stage | Base image | Purpose |
|---|---|---|
| `deps` | `node:22-alpine` | `npm ci` — install all deps from lockfile |
| `builder` | `node:22-alpine` | `npm run build` producing `.next/standalone/` |
| `runner` | `node:22-alpine` | Copy standalone bundle only; run as non-root `nextjs` |

Key decisions:
- `output: 'standalone'` must be added to `next.config.ts` (one-line change)
- `NEXT_TELEMETRY_DISABLED=1` set in builder stage
- `NEXT_PUBLIC_API_URL` passed as a build ARG (baked into the JS bundle at build time)
- Final image only contains `.next/standalone/`, `.next/static/`, and `public/`
- `HEALTHCHECK` hits `GET /` via wget

### AI-Chat (`ai-chat/Dockerfile`)

Same uv-workspace pattern as backend. No `CMD` — container is invoked on demand.

| Stage | Base image | Purpose |
|---|---|---|
| `builder` | `python:3.12-slim` | Install uv, run `uv sync --frozen --no-dev` |
| `runtime` | `python:3.12-slim` | Copy `.venv` + ai-chat source; non-root user |

`WORKDIR` set to `/app/ai-chat`. No default command.

Usage:
```bash
docker compose --profile tools run ai-chat python main.py
```

---

## Compose Files

### `docker-compose.yml` (base)

Defines all services, shared network, and volumes. Backend port 8000 exposed for local testing only.

Key configuration:
- backend: env_file, bind mount `./data/fixtures:/app/fixtures`, healthcheck on `/healthz`
- frontend: build ARG for `NEXT_PUBLIC_API_URL`, `depends_on: backend` (healthy), port 3000
- ai-chat: `profiles: ["tools"]` — never starts with plain `docker compose up`
- tunnel: `cloudflare/cloudflared:latest`, `TUNNEL_TOKEN` from env, depends on both services healthy

### `docker-compose.prod.yml` (production override)

- `ports: []` on backend and frontend (removes all host port exposure)
- `restart: unless-stopped` on backend, frontend, tunnel
- Resource limits: backend 1 CPU / 1G RAM, frontend 0.5 CPU / 512M RAM

**Production deployment command:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Environment & Secrets

### `.env` (never committed)

```bash
GOOGLE_API_KEY=<your-google-api-key>
CLOUDFLARE_TUNNEL_TOKEN=<your-cloudflare-tunnel-token>
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### `.env.example` (committed)

```bash
GOOGLE_API_KEY=
CLOUDFLARE_TUNNEL_TOKEN=
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

`.env` must be in `.gitignore`. `.env.example` is committed as a reference.

---

## `.dockerignore` Files

**Monorepo root `.dockerignore`** (backend + ai-chat builds):
- Excludes: `.git`, `.venv`, `node_modules`, `__pycache__`, `frontend/`, `.agents/`, `.claude/`, `docs/`, test files

**`frontend/.dockerignore`**:
- Excludes: `node_modules`, `.next`, `__pycache__`, `.env*`, `*.md`

---

## Best Practices Checklist

| Practice | Applied |
|---|---|
| Non-root user in all runtime stages | ✅ |
| `.dockerignore` per build context | ✅ |
| Lockfile-pinned installs (`--frozen` / `npm ci`) | ✅ |
| Minimal final image (build tools excluded) | ✅ |
| `HEALTHCHECK` on backend + frontend | ✅ |
| `depends_on` with health condition | ✅ |
| No secrets in image layers | ✅ (env_file at runtime) |
| `NEXT_TELEMETRY_DISABLED=1` | ✅ |
| Next.js standalone output | ✅ |
| Resource limits in prod | ✅ |
| `restart: unless-stopped` in prod | ✅ |
| No host ports in prod | ✅ (tunnel handles ingress) |
| `ai-chat` isolated behind profile | ✅ |

---

## Files to Create / Modify

```
eval-platform/
├── docker-compose.yml              # NEW
├── docker-compose.prod.yml         # NEW
├── .env.example                    # NEW
├── .dockerignore                   # NEW (monorepo root)
├── backend/
│   └── Dockerfile                  # NEW
├── frontend/
│   ├── Dockerfile                  # NEW
│   ├── .dockerignore               # NEW
│   └── next.config.ts              # MODIFY: add output: 'standalone'
├── ai-chat/
│   └── Dockerfile                  # NEW
└── data/
    └── fixtures/                   # NEW dir (bind mount target, gitignored)
```

## Out of Scope

- CI/CD pipeline (GitHub Actions, etc.)
- SSL termination (handled by Cloudflare)
- Database migrations (no traditional DB — file-based persistence)
- Horizontal scaling / orchestration (single VM, Compose only)
