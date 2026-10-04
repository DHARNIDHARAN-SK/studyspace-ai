# StudySpace AI

Multi-tenant academic document intelligence SaaS for students and independent learners.

StudySpace AI allows students to organize academic materials by project, ask questions grounded strictly in their uploaded documents, inspect verified citations, maintain revision checklists, generate source-grounded quizzes, and export study materials. It also exposes a secured platform developer API.

## Architecture & Documentation

- [Master Architecture Specification](STUDYSPACE_AI_MASTER_ARCHITECTURE.md)
- [Project Status & Current State](docs/PROJECT_STATUS.md)
- [Architecture Decisions (ADRs)](docs/DECISIONS.md)
- [Master Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [Infrastructure & Deployment Guide](infra/deployment/README.md)

## Repository Structure

```text
studyspace-ai/
├── apps/
│   └── web/                         # React + Vite + TypeScript frontend
│       ├── src/
│       │   ├── app/                 # Main shell & components
│       │   ├── lib/                 # API client & helpers
│       │   ├── styles/              # Tailwind CSS styles
│       │   └── types/               # TypeScript interfaces
│       └── package.json
├── services/
│   └── api/                         # FastAPI backend service
│       ├── app/
│       │   ├── main.py              # Application entrypoint
│       │   ├── api/v1/              # Versioned API routes
│       │   ├── core/                # Settings, logging, errors
│       │   └── db/                  # Database session & connections
│       ├── tests/                   # Pytest test suite
│       └── pyproject.toml
├── supabase/
│   └── migrations/                  # Versioned PostgreSQL + pgvector migrations
├── infra/
│   ├── docker/                      # Dockerfile.api and Dockerfile.web
│   ├── compose/                     # docker-compose.yml for local development
│   └── deployment/                  # Deployment documentation
├── docs/                            # Project status, ADRs, implementation plan
├── .env.example                     # Environment configuration template
└── package.json                     # Monorepo development scripts
```

## Canonical Single-Command Local Startup

To launch all StudySpace AI services with automated Ollama model verification, Docker containers (PostgreSQL 16 with pgvector, Redis 7, FastAPI, and Vite web UI), and health probes:

```powershell
# Start all services
.\scripts\start.ps1

# Stop all services
.\scripts\stop.ps1
```

### Access Endpoints
- **Web Application:** `http://localhost:3000` (Docker) or `http://localhost:5173` (Local Dev)
- **FastAPI Backend:** `http://localhost:8000`
- **Interactive OpenAPI Docs:** `http://localhost:8000/docs`
- **Health Check Probe:** `http://localhost:8000/api/v1/health`
- **Ollama Local LLM:** `http://localhost:11434` (`nomic-embed-text:latest` & `phi4-mini:latest`)

---

## Developer API & Security (Phase 11)

StudySpace AI provides a secure programmatic API authenticated via API Keys (`sk_live_...`):

- **Key Management (Web Dashboard):**
  - `POST /api/v1/developer/keys` — Generate scoped API key (hashed at rest with SHA-256)
  - `GET /api/v1/developer/keys` — List workspace API keys (secret masked)
  - `DELETE /api/v1/developer/keys/{id}` — Revoke API key immediately
  - `GET /api/v1/developer/usage` — View usage event audits and token consumption
- **Programmatic Endpoints (`X-API-Key: sk_live_...` or `Authorization: Bearer sk_live_...`):**
  - `POST /api/v1/dev/chat` — Programmatic grounded RAG chat (Scope: `chat:write`)
  - `POST /api/v1/dev/retrieve` — Hybrid candidate chunk retrieval (Scope: `retrieval:read`)
  - `GET /api/v1/dev/projects/{id}/revision` — Access project revision checklist (Scope: `revision:read`)
- **Rate Limiting:** Token-bucket rate limiting (100 req/min) with Redis backend and automatic 429 back-off headers (`Retry-After: 60`).

---

## Running Automated Tests

```powershell
# Run backend pytest suite (Phase 6-11 tests)
.venv\Scripts\pytest services/api/tests

# Run frontend Vitest test suite
npm.cmd test --prefix apps/web -- --run

# Run web production build typecheck
npm.cmd run build --prefix apps/web
```

