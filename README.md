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

## Quickstart

### 1. Backend Service (FastAPI)
```bash
# Activate virtual environment
.venv\Scripts\activate

# Run backend API server
uvicorn app.main:app --app-dir services/api --reload --port 8000
```
Health endpoint: `http://localhost:8000/api/v1/health`

### 2. Frontend Service (Vite + React)
```bash
# Navigate to web application
cd apps/web

# Install packages & run dev server
npm install
npm run dev
```
Web client: `http://localhost:5173`

### 3. Running Tests
```bash
# Run backend pytest suite
pytest services/api/tests

# Run frontend build check
npm --prefix apps/web run build
```
