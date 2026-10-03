# StudySpace AI — Deployment & Infrastructure Architecture

## Architecture Deployment Boundaries (Section 5.2)

1. **Frontend (apps/web)**:
   - Hosted on Vercel.
   - Built via Vite + React + TypeScript.
   - Static client-side routing.
   - Uses Supabase public client for auth and direct short-lived requests where appropriate.

2. **Backend API (services/api)**:
   - Hosted as a persistent containerized service (e.g. Render, Railway, AWS ECS, or Fly.io).
   - FastAPI application serving REST endpoints under `/api/v1` and external developer endpoints under `/v1`.
   - Never exposes server-side provider credentials to the client.

3. **Background Worker (Celery)**:
   - Persistent worker processes for long-running document ingestion (PDF extraction, OCR, batch embedding, re-indexing).
   - Scales separately from the API web process.

4. **Data Layer**:
   - Supabase PostgreSQL with `pgvector` for vector storage and full-text search (`tsvector`) for lexical retrieval.
   - Supabase Storage: Private buckets for uploaded student materials and generated exports.
   - Upstash / Redis: Message broker for Celery tasks and short-lived caching / rate-limiting.
