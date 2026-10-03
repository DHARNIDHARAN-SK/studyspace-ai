# StudySpace AI — Architecture Decision Records (ADRs)

This document records the architectural and engineering decisions actually made during the implementation of StudySpace AI.

---

## ADR-001: Monorepo Project Structure
- **Date:** 2026-10-03
- **Context:** StudySpace AI requires a web frontend, a persistent FastAPI backend, a background task worker, shared contracts, database migrations, and infrastructure definitions.
- **Decision:** Adopt the monorepo layout specified in Section 14 of the Master Architecture:
  - `apps/web`: React + Vite + TypeScript frontend.
  - `services/api`: FastAPI backend service and domain modules.
  - `supabase/migrations`: Versioned SQL migrations for Supabase PostgreSQL/pgvector.
  - `infra/`: Docker definitions and local compose configuration.
  - `docs/`: Project status, architecture records, and specifications.
- **Consequences:** Ensures clean separation of concerns while allowing atomic changes and unified development tooling across frontend and backend.

---

## ADR-002: Backend Runtime & Dependency Management
- **Date:** 2026-10-03
- **Context:** Python 3.12 is the target runtime. Fast and reproducible dependency installation is needed across local development and CI/CD.
- **Decision:** Use `uv` for virtual environment management and package resolution, with `pyproject.toml` as the standard project specification file for `services/api`.
- **Consequences:** Near-instant dependency resolution and installation without relying on legacy pip/requirements.txt drift.

---

## ADR-003: Configuration and Secret Isolation
- **Date:** 2026-10-03
- **Context:** Master Architecture Sections 8.3 & 15 require strict separation between client-safe variables and server-side secrets, with zero secrets in source control.
- **Decision:**
  - Create `.env.example` at root, `apps/web/.env.example`, and `services/api/.env.example` containing only safe placeholder names.
  - Use `pydantic-settings` in the backend to validate environment variables at startup.
  - Prefix all frontend-exposed variables with `VITE_`.
  - Add all `.env` files and certificates to `.gitignore`.
- **Consequences:** Prevents accidental leakage of Supabase service role keys, database passwords, or model provider API keys.

---

## ADR-004: Structured, Non-Sensitive Error Responses
- **Date:** 2026-10-03
- **Context:** Master Architecture Section 16 mandates that the UI and API must provide clear error handling with safe error codes and useful next actions, without exposing stack traces, database errors, or credentials.
- **Decision:** Implement `AppError` and global FastAPI exception handlers returning a uniform payload schema:
  `{ "error": { "code": string, "message": string, "action": string | null, "details": object } }`.
- **Consequences:** Consistent, secure, and actionable error handling across all API endpoints.

---

## ADR-005: Supabase Migration Foundation & Row Level Security
- **Date:** 2026-10-03
- **Context:** Master Architecture Section 10 defines 18 core entities, vector embeddings, lexical search, and multi-tenant isolation.
- **Decision:**
  - Create `supabase/migrations/20261003000001_initial_schema.sql` defining all 18 tables, indices, foreign keys, `pgvector(768)`, and `tsvector` columns.
  - Explicitly enable Row Level Security (RLS) on all user-accessible tables with workspace-scoping policies.
  - Retain local migration files without modifying remote production databases prematurely.
- **Consequences:** Ensures reproducible, versioned schema state compatible with Supabase CLI and local Docker containers.

---

## ADR-006: JWT Bearer Authentication & Pluggable Token Verification
- **Date:** 2026-10-03
- **Context:** The FastAPI backend must validate Supabase Auth tokens passed from the client while remaining 100% testable in offline local environments without relying on third-party network calls.
- **Decision:** Implement a FastAPI dependency (`get_current_user`) using `PyJWT` that verifies tokens against `SUPABASE_JWT_SECRET` when configured, and supports standard HMAC verification for development/testing tokens. Automatically extract the user identity (`sub`) and ensure their application profile and personal workspace are provisioned idempotently.
- **Consequences:** Strong cryptographic authentication with seamless offline and CI testability.

---

## ADR-007: Strict Multi-Tenant Workspace Scoping
- **Date:** 2026-10-03
- **Context:** Section 1.3 (Principle 2) mandates: "Users must never retrieve another user's documents, chunks, chats, quizzes, exports, or cached answers."
- **Decision:** Every project CRUD operation must resolve the authenticated user's workspace ID and query the data store using the composite key `(project_id, workspace_id)`. If User A requests a resource belonging to User B, the API returns HTTP 404 (Not Found) rather than disclosing existence. Direct API access without valid tokens returns HTTP 401.
- **Consequences:** Prevents Insecure Direct Object Reference (IDOR) attacks at the backend layer regardless of frontend checks.

---

## ADR-008: SPA Routing with Protected Layout Shell
- **Date:** 2026-10-03
- **Context:** Students need seamless project switching, navigation between learning tools, and persistent context across views.
- **Decision:** Use `react-router-dom` with a `ProtectedRoute` wrapper guarding the `AppShell`. Provide a persistent left sidebar on desktop with project selector and a mobile drawer. The client stores no server secrets and communicates only with Supabase Auth (via public anon key) and the backend API (via Bearer token).
- **Consequences:** Responsive, accessible application shell adhering to education SaaS UX patterns.

---

## ADR-009: HNSW Vector Indexing Strategy with Cosine Distance
- **Date:** 2026-10-03
- **Context:** Master Architecture Section 6 & 10 requires 768-dimensional dense vector embeddings (`nomic-embed-text`) with high-recall retrieval. An index strategy is needed for `document_chunks.embedding`.
- **Decision:** Use pgvector's HNSW (Hierarchical Navigable Small World) index with `vector_cosine_ops` (`idx_chunks_embedding_hnsw`).
- **Consequences:** Unlike IVFFlat, HNSW does not require pre-populating or training a cluster list before creating the index. It supports incremental chunk additions with low query latency and high recall out-of-the-box.

---

## ADR-010: Asynchronous SQLAlchemy 2.0 with asyncpg and Contextual NullPool
- **Date:** 2026-10-03
- **Context:** The FastAPI backend requires non-blocking asynchronous database operations. Under pytest-asyncio on Windows, connection pooling across test-scoped event loops causes socket termination collisions.
- **Decision:** Standardize on SQLAlchemy 2.0 async engine (`create_async_engine`) and `asyncpg`. In production and normal runtime, use `AsyncAdaptedQueuePool` (pool size 10, max overflow 20, pre-ping enabled). Under automated testing environments, dynamically switch to `NullPool` so connections close within the active event loop.
- **Consequences:** Maximizes production throughput via pooling while providing rock-solid, race-condition-free test execution.

---

## ADR-011: Canonical Tenant Storage Hierarchy and Defensive File Path Validation
- **Date:** 2026-10-03
- **Context:** Student documents and generated study materials must be strictly isolated to prevent cross-tenant exposure or path traversal attacks.
- **Decision:** Enforce canonical storage hierarchy:
  `workspaces/{workspace_id}/projects/{project_id}/documents/{document_id}/{filename}`
  and for exports:
  `workspaces/{workspace_id}/exports/{export_id}/{filename}`.
  All upload operations must sanitize filenames, strip traversal elements (`..`, `\`, leading `/`, null bytes), validate UUID segments, and enforce workspace ownership before any storage or database write.
- **Consequences:** Eliminates storage traversal, cross-workspace leakage, and namespace collisions across private buckets.

---

## ADR-012: Full SaaS Routing Structure (Public Marketing & Protected Learning Shell)
- **Date:** 2026-10-03
- **Context:** Students and prospective academic partners require public discovery pages (`/`, `/about`, `/features`, `/contact`) while students need a protected application shell (`/dashboard`, `/projects`, `/projects/:projectId`, `/settings`, `/developer`).
- **Decision:** Implement client-side routing using `react-router-dom` with separate layout trees: public pages use `PublicHeader` and `PublicFooter`, while authenticated routes are nested within `ProtectedRoute` and `AppShell`. Authenticated visitors accessing `/login` or `/signup` are automatically redirected to `/dashboard`.
- **Consequences:** Clean separation between unauthenticated marketing discovery and private study tools.

---

## ADR-013: Modular Project Workspace Tabs with Explicit Roadmap Boundaries
- **Date:** 2026-10-03
- **Context:** The project workspace must host 5 distinct learning tools (`Chat`, `Sources`, `Revision`, `Quizzes`, `Study Guides`) without implementing backend ingestion or RAG pipelines prematurely.
- **Decision:** Deconstruct the workspace into dedicated, typed React tab components. For capabilities activating in later roadmap phases (such as Celery document ingestion in Phase 5, RAG retrieval in Phase 6, or PDF export in Phase 7), present clean UI controls with informative boundary notices rather than fake mock content.
- **Consequences:** Provides a polished, accessible, production-grade interface that seamlessly connects to backend microservices as they are built.

---

## ADR-014: Protected Answer Key Architecture for Source-Grounded Quizzes
- **Date:** 2026-10-03
- **Context:** Master Architecture Section 4.4 and 10 mandate that students must not see quiz answer keys or explanations prior to attempt submission.
- **Decision:** In the frontend quiz interface, hide expected answers and detailed syllabus citation explanations during question selection. The evaluation UI only reveals correctness badges and underlying citations once the user triggers "Submit Attempt".
- **Consequences:** Enforces genuine active recall for students, aligning frontend behavior with the upcoming backend quiz evaluation service.
---

## ADR-015: Structure-Aware Parsing & Provenance Preservation Architecture
- **Date:** 2026-10-03
- **Context:** Master Architecture Section 6 mandates that documents must not be parsed blindly or chunked with uniform fixed-length cuts across all formats. Future citation features require fine-grained location tracking (page numbers for PDFs, slide numbers/titles for PPTX, and heading hierarchies for DOCX and Markdown).
- **Decision:** Implement dedicated parser implementations in `app.rag.parsing` adhering to `BaseParser` returning structured `ParsedBlock` and `ParsedDocument` intermediate objects:
  - `pypdf`: Extracts page-by-page to safely handle up to 500-page academic documents; detects headings through typographic heuristics; identifies scanned documents when text density is near zero.
  - `python-docx`: Retains heading levels to construct hierarchical `section_path` strings (`Chapter 1 > 1.1 Overview`); extracts paragraphs and tables.
  - `python-pptx`: Extracts slide numbers (1-indexed), slide titles, text blocks, and presenter notes.
  - `TextParser`: Preserves Markdown headings (`#` to `######`), code blocks, bullet lists, and source line numbers.
- **Consequences:** All downstream chunks maintain stable, verified academic provenance suitable for exact citations.

---

## ADR-016: Celery Background Ingestion Worker and Non-Blocking Upload Flow
- **Date:** 2026-10-03
- **Context:** The system must process documents up to 500 pages (e.g. 300+ page course textbooks). Processing such files synchronously in HTTP request cycles causes gateway timeouts (504) and client connection drops.
- **Decision:** In the upload endpoint (`POST /api/v1/projects/{project_id}/documents`), validate the file, store it in private storage, create a `queued` Document record and IngestionJob, dispatch an asynchronous task to Celery via Redis broker, and return immediately with HTTP 202 Accepted. The persistent Celery worker handles parsing, chunking, and database persistence asynchronously.
- **Consequences:** Upload endpoints respond in < 100ms regardless of document size. Large files (e.g., 327-page textbook) are processed in background workers without memory leaks or request timeouts.

---

## ADR-017: Atomic Transactional Idempotency for Document Chunk Persistence
- **Date:** 2026-10-03
- **Context:** Background workers can retry due to network glitches or transient errors. Accidental duplicate executions of an ingestion task must not double or multiply chunk records in `document_chunks`.
- **Decision:**
  1. On upload, compute SHA-256 checksum and check for identical existing indexed documents in the project to avoid redundant worker tasks.
  2. Inside the worker ingestion pipeline, execute chunk persistence inside an atomic database transaction: delete any existing chunks for `(document_id, document_version)` prior to bulk inserting new chunks.
  3. Update `Document.ingestion_status = 'indexed'` and `IngestionJob.status = 'completed'` atomically within the same transaction.
- **Consequences:** Safe, completely idempotent worker retries and re-indexing without duplicate chunk sets or database deadlocks.

---

## ADR-018: Local Baseline RAG Pipeline with Ollama (nomic-embed-text & phi4-mini)
- **Date:** 2026-10-03
- **Context:** Phase 6 requires establishing the first working baseline RAG pipeline. Local development and testing through Phase 11 strictly mandates local Ollama inference without cloud dependencies or paid APIs (no Gemini). Database schema requires 768-dimensional dense vectors with HNSW cosine indexing.
- **Decision:**
  1. **Provider Abstraction:** Implement `BaseEmbeddingProvider` and `BaseLLMProvider` interfaces extensible for future providers, with active factory resolution strictly pointing to local Ollama.
  2. **Embedding Model & Dimensions:** Use `nomic-embed-text:latest` producing 768-dimensional vectors. Validate `len(vector) == 768` prior to database writes with `DimensionMismatchError`.
  3. **Batch Chunk Embedding:** Implement `ChunkEmbeddingService` processing chunks in batches of 32 via Ollama `/api/embed`. Skip re-embedding already embedded chunks to ensure idempotency.
  4. **Dense Vector Retrieval:** Implement `VectorRetriever` computing query embeddings and querying PostgreSQL via pgvector's cosine distance `<=>` operator (accelerated by `idx_chunks_embedding_hnsw`).
  5. **Strict Multi-Tenant Isolation:** Enforce `workspace_id` and `project_id` filters in retrieval and chat queries. Verified with negative cross-tenant automated tests.
  6. **Context Construction & Citations:** `ContextBuilder` aggregates retrieved chunks, eliminates duplicate content, limits text to 8,000 characters, and constructs verifiable `[Document, p. X]` citation metadata.
  7. **Grounded Baseline Prompt:** Prompt `phi4-mini:latest` to answer strictly based on provided context excerpts and explicitly emit an insufficient-evidence statement if the query is not covered by the documents.
  8. **Conversation Persistence & Chat API:** Implement `ChatService` persisting user/assistant turns in `conversations`, `messages`, and `message_citations`. Connect to frontend `ChatTab.tsx` with real citation inspection, latency measurement, and model badge.
  9. **Phase Boundaries:** Advanced retrieval (BM25, reciprocal rank fusion, cross-encoder reranking) and query transformations (rewriting, decomposition) are strictly excluded from Phase 6 and deferred to Phase 7 and 8.
- **Consequences:** Zero-cost, 100% offline baseline RAG with full citation traceability, verified on the real 327-page textbook `DECAP470_CLOUD_COMPUTING.pdf`.

