# Docker Compose Deployment

## Goal
Containerize backend, frontend, and ai-chat services with multi-stage Dockerfiles, Cloudflare Tunnel, and a base + prod override Compose setup ready for cloud VM deployment.

## Tasks

- [ ] **Task 1: Root `.dockerignore`** — Create monorepo-root `.dockerignore` excluding `.git`, `.venv`, `node_modules`, `__pycache__`, `frontend/`, `.agents/`, `.claude/`, `docs/`, `*.md`, `tests/`
  → Verify: `docker build` for backend doesn't copy irrelevant files (check with `--progress=plain`)

- [ ] **Task 2: `backend/Dockerfile`** — Write 2-stage build: `builder` (python:3.12-slim, install uv, `uv sync --frozen --no-dev --package backend`), `runtime` (python:3.12-slim, non-root `appuser`, copy `.venv` + `backend/app` + `backend/fixtures`). HEALTHCHECK `curl -f http://localhost:8000/healthz`. CMD `uvicorn app.main:app --host 0.0.0.0 --port 8000`
  → Verify: `docker build -f backend/Dockerfile .` completes without error

- [ ] **Task 3: `frontend/next.config.ts`** — Add `output: 'standalone'` to `nextConfig` object (one-line change)
  → Verify: file contains `output: 'standalone'`

- [ ] **Task 4: `frontend/.dockerignore`** — Create `frontend/.dockerignore` excluding `node_modules`, `.next`, `__pycache__`, `.env*`, `*.md`, `.superpowers`
  → Verify: file exists at `frontend/.dockerignore`

- [ ] **Task 5: `frontend/Dockerfile`** — Write 3-stage build: `deps` (node:22-alpine, `npm ci`), `builder` (node:22-alpine, copy deps + src, `NEXT_TELEMETRY_DISABLED=1`, build ARG `NEXT_PUBLIC_API_URL`, `npm run build`), `runner` (node:22-alpine, non-root `nextjs:nodejs`, copy `.next/standalone`, `.next/static`, `public`). HEALTHCHECK `wget -qO- http://localhost:3000`. CMD `node server.js`
  → Verify: `docker build -f frontend/Dockerfile frontend/` completes without error

- [ ] **Task 6: `ai-chat/Dockerfile`** — Write 2-stage build: `builder` (python:3.12-slim, install uv, `uv sync --frozen --no-dev --package ai-chat`), `runtime` (python:3.12-slim, non-root `appuser`, copy `.venv` + `ai-chat/` source). WORKDIR `/app/ai-chat`. No CMD.
  → Verify: `docker build -f ai-chat/Dockerfile .` completes without error

- [ ] **Task 7: `docker-compose.yml`** — Write base compose: backend (build context `.`, env_file `.env`, volume `./data/fixtures:/app/fixtures`, healthcheck), frontend (build context `./frontend`, build arg `NEXT_PUBLIC_API_URL`, depends_on backend healthy, port `3000:3000`), ai-chat (build context `.`, profiles `["tools"]`, volume `./data/fixtures:/app/fixtures`), tunnel (`cloudflare/cloudflared:latest`, cmd `tunnel --no-autoupdate run`, env `TUNNEL_TOKEN`, depends_on frontend+backend healthy). Network `eval-net`.
  → Verify: `docker compose config` validates without errors

- [ ] **Task 8: `docker-compose.prod.yml`** — Write prod override: backend (`restart: unless-stopped`, `ports: []`, resource limits `1 CPU / 1G`), frontend (`restart: unless-stopped`, `ports: []`, resource limits `0.5 CPU / 512M`), tunnel (`restart: unless-stopped`)
  → Verify: `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` validates

- [ ] **Task 9: `.env.example` + `.gitignore`** — Create `.env.example` with keys `GOOGLE_API_KEY`, `CLOUDFLARE_TUNNEL_TOKEN`, `NEXT_PUBLIC_API_URL`. Ensure `.env` and `data/fixtures/` are in root `.gitignore`. Create `data/fixtures/.gitkeep`.
  → Verify: `git check-ignore .env` returns `.env`; `data/fixtures/.gitkeep` exists

- [ ] **Task 10: Smoke test** — Run `docker compose up --build -d` locally, check `docker compose ps` shows backend + frontend healthy, tunnel connected. Hit `http://localhost:3000` and `http://localhost:8000/healthz`.
  → Verify: all containers `healthy`, no crash loops

## Done When
- [ ] `docker compose up --build` starts backend + frontend healthy
- [ ] Tunnel container starts without error (given valid `CLOUDFLARE_TUNNEL_TOKEN`)
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` validates cleanly
- [ ] `.env` is gitignored; `.env.example` is committed
- [ ] `docker compose --profile tools run ai-chat python --version` runs successfully

## Notes
- Backend build context must be monorepo root (`context: .`) — `sdk/` is a local workspace dep
- `NEXT_PUBLIC_API_URL` is baked at build time (Next.js ARG, not runtime env)
- `ai-chat` never starts automatically — requires `--profile tools`
- `data/fixtures/` is bind-mounted so data survives container rebuilds
