# StudySpace AI — Master Implementation Plan

This roadmap translates `STUDYSPACE_AI_MASTER_ARCHITECTURE.md` into phased, testable engineering milestones.

---

## Phase 1: Foundation & Environment Setup [COMPLETED]
- [x] Monorepo directory structure established (`apps/web`, `services/api`, `supabase/migrations`, `infra`, `docs`).
- [x] Python backend foundation with FastAPI, Uvicorn, Pydantic-Settings, and Pytest.
- [x] Frontend foundation with React 18, Vite, TypeScript, and Tailwind CSS.
- [x] Environment configuration templates (`.env.example` at root and services).
- [x] Database migration baseline (`supabase/migrations/20261003000001_initial_schema.sql`) covering all 18 entities, pgvector, and RLS.
- [x] Structured, non-sensitive error handling and logging foundation.
- [x] Health check endpoints (`/health` and `/api/v1/health`) verified with automated tests.
- [x] Docker configuration for local development (`Dockerfile.api`, `Dockerfile.web`, `docker-compose.yml`).
- [x] Production build verification (`npm run build` passing with zero errors).
- [x] Project continuity documentation (`PROJECT_STATUS.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`).

---

## Phase 2: Authentication, Workspaces, and Projects Management [COMPLETED]
- [x] Supabase Auth client integration on frontend (Email/Password, OAuth providers).
- [x] User profile provisioning trigger on new signup.
- [x] Workspace and project domain models, CRUD API routes (`/api/v1/projects`).
- [x] Authenticated application shell with persistent left navigation sidebar and project switcher.
- [x] Student dashboard baseline (recent projects, empty states).
- [x] Automated authorization and multi-tenant isolation unit and integration tests.

---

## Phase 3: Database, Storage & Data Model Hardening [COMPLETED]
- [x] Complete 19-table schema migration with foreign key cascading and data integrity constraints.
- [x] pgvector (0.8.7) extension and 768-dim HNSW vector index (`idx_chunks_embedding_hnsw`) with cosine distance.
- [x] Automated full-text search update trigger on `document_chunks` for lexical search (`tsvector`).
- [x] Row-Level Security (RLS) enabled and verified on all 19 public tables.
- [x] Private Supabase Storage foundation with canonical tenant hierarchy, path traversal security, and MIME/size limits.
- [x] Typed SQLAlchemy 2.0 async ORM models, async engine, session lifecycle, and connection health probes.
- [x] Automated unit and integration test suite (24/24 tests passing).

---

## Phase 4: Document Ingestion, Parsing, Chunking & Celery Workers
- [ ] Asynchronous Celery ingestion worker setup with Redis broker.
- [ ] Format parsers for `.pdf` (up to 500-page target with batching and scanned detection), `.docx`, `.pptx`, `.txt`, `.md`.
- [ ] Structure-aware chunking pipeline retaining page/slide/section provenance.
- [ ] Document processing lifecycle state management (`uploaded`, `extracting`, `chunking`, `indexed`, `failed`).
- [ ] Ingestion retry and deduplication idempotency tests.

---

## Phase 4: Embeddings, Vector Storage & Hybrid Retrieval
- [ ] Provider abstraction for Embedding models (local Ollama nomic-embed-text / hosted alternatives).
- [ ] Batch vector generation and pgvector storage with dimension consistency checks.
- [ ] PostgreSQL full-text search index (`tsvector`) generation for lexical search.
- [ ] Parallel retrieval implementation (dense vector similarity + lexical full-text query) strictly scoped to user/workspace/project.
- [ ] Retrieval tests verifying isolation and accuracy.

---

## Phase 5: Fusion, Reranking, Grounded Generation & Citations
- [ ] Reciprocal Rank Fusion (RRF) combining dense and lexical search candidates.
- [ ] Reranking provider interface and candidate filtering.
- [ ] Generation provider adapters for local Ollama (Llama 3.2) and hosted Gemini.
- [ ] Evidence-first system prompt enforcing citation tagging and abstention on insufficient context.
- [ ] Citation validation engine comparing model citations against retrieved chunk IDs and stored page/slide metadata.
- [ ] End-to-end conversation flow and streaming response handling.

---

## Phase 6: Student Learning Tools
- [ ] Project-contained Revision Checklist (`not_started`, `learning`, `revised`) with links to sources and conversations.
- [ ] Source-grounded Quiz Generator (MCQ, short-answer, challenge questions).
- [ ] Protected answer keys (answers and explanations hidden until attempt submission).
- [ ] Quiz attempt tracking and review interface.
- [ ] Source-grounded Study Guide generation and persistence.

---

## Phase 7: Export Engine & Query Rewriting UX
- [ ] Single response and full conversation export to PDF and DOCX.
- [ ] Configurable transcript limits (10, 15, 20 pages max) with explicit overflow handling.
- [ ] Query rewriting UX with user toggle (option to use proposed query or retain original).

---

## Phase 8: Platform Developer REST API
- [ ] Scoped API key generation with cryptographic hashing at rest.
- [ ] External API routes (`/v1/chat/completions` or `/v1/query`).
- [ ] Per-key and per-workspace rate limiting and usage tracking.
- [ ] Interactive OpenAPI / Swagger documentation for developers.

---

## Phase 9: Evaluation Suite, Architecture Views & Observability
- [ ] LikeC4 architecture views and diagrams matching real implementation.
- [ ] RAG evaluation benchmark harness (Recall@k, MRR, Faithfulness, Citation accuracy).
- [ ] Structured telemetry and usage metrics without logging private documents or secrets.

---

## Phase 10: Production Deployment & Verification
- [ ] Frontend deployment to Vercel.
- [ ] Backend API and Celery workers deployed to persistent container host.
- [ ] Managed Supabase and Upstash Redis production configuration verification.
- [ ] End-to-end smoke tests and multi-tenant security verification.
