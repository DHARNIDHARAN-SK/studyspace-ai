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

## Phase 4: Frontend SaaS UI & Project Workspace [COMPLETED]
- [x] Public marketing and informational routes (`/`, `/about`, `/features`, `/contact`).
- [x] Student authentication and registration flows (`/login`, `/signup`) with validation and tenant switcher.
- [x] Authenticated application shell with persistent desktop sidebar, mobile responsive drawer, and project switcher.
- [x] Student overview dashboard with real project metrics and empty state CTA.
- [x] Dedicated projects directory (`/projects`) with live search, discipline pills, edit and delete modals.
- [x] Complete project workspace (`/projects/:projectId`) with 5 dedicated tabs:
  - Grounded Chat: conversation sidebar, query rewriter toggle, verifiable citation inspector, and composer.
  - Sources & Documents: document list with metadata (file size, slide/page count) and indexing status badges.
  - Revision Checklist: syllabus topic progress bar, status selector, and topic creation modal.
  - Quizzes: interactive quiz assessment with protected answer keys and post-submission explanations.
  - Study Guides: formatted review canvas, printable view, and export notice.
- [x] Settings console (`/settings`) for student profile, citation style, and session controls.
- [x] Developer platform API console (`/developer`) for scoped API key generation and sample cURL requests.
- [x] End-to-end verification of 11 critical flows via Playwright MCP.
- [x] Production build verified (`tsc -b && vite build` passing).

---

## Phase 5: Document Ingestion, Parsing, Chunking & Celery Workers
- [x] Asynchronous Celery ingestion worker setup with Redis broker.
- [x] Format parsers for `.pdf` (up to 500-page target with batching and scanned detection), `.docx`, `.pptx`, `.txt`, `.md`.
- [x] Structure-aware chunking pipeline retaining page/slide/section provenance.
- [x] Document processing lifecycle state management (`uploaded`, `extracting`, `chunking`, `indexed`, `failed`).
- [x] Ingestion retry and deduplication idempotency tests.
- [x] Controlled real 327-page textbook verification (`DECAP470_CLOUD_COMPUTING.pdf` producing 1,728 chunks).
- [x] Frontend Sources UI integrated with real backend upload and status polling.

---

## Phase 6: Embeddings & Baseline Vector RAG
- [x] Provider abstraction for Embedding models (`BaseEmbeddingProvider`, `OllamaEmbeddingProvider` using `nomic-embed-text:latest`).
- [x] Dimension consistency validation (strictly enforcing 768 dimensions matching pgvector schema).
- [x] Batch chunk embedding service with idempotency guards (`ChunkEmbeddingService`).
- [x] Dense vector similarity retrieval service backed by pgvector HNSW index (`VectorRetriever`).
- [x] Strict multi-tenant isolation enforced at database query level (`workspace_id` + `project_id`) with negative tests.
- [x] Traceable context construction and structured citation mapping (`ContextBuilder`).
- [x] Grounded baseline prompt with strict insufficient-evidence abstention rules.
- [x] LLM provider abstraction and local Ollama implementation (`phi4-mini:latest`).
- [x] Chat API endpoints and conversation/message persistence (`ChatService`).
- [x] Frontend Chat UI integrated with real RAG responses, citations, latency display, and `phi4-mini:latest` badge.
- [x] Real 327-page textbook verification (`DECAP470_CLOUD_COMPUTING.pdf` 1,728 chunks embedded and queried).

---

## Phase 7: Fusion, Reranking, Grounded Generation & Citations
- [x] Lexical Full-Text Search retriever (`LexicalRetriever`) backed by PostgreSQL `tsvector` and length-normalized ranking.
- [x] Reciprocal Rank Fusion (`ReciprocalRankFusion`) combining dense and lexical search candidates with configurable smoothing ($k=60$).
- [x] Reranking provider interface (`BaseReranker`) and deterministic `LocalCrossEncoderReranker`.
- [x] Strict model guardrails preventing unrequested model/library downloads (`RerankerModelNotFoundError`).
- [x] End-to-end Hybrid RAG Pipeline (`AdvancedRAGPipeline`) with multi-path metrics and citation provenance.
- [x] Dual-mode support (`RAG_RETRIEVAL_MODE=baseline|advanced`) in backend and frontend toggle in `ChatTab.tsx`.
- [x] Controlled evaluation experiment on 327-page textbook `DECAP470_CLOUD_COMPUTING.pdf` across 4 domain queries.

---

## Phase 8: Conversational RAG, Query Transformation, Multi-Query & Semantic Cache
- [x] Bounded conversation context manager (`ConversationContextManager`) extracting recent turns chronologically with strict workspace isolation.
- [x] Contextual query rewriting (`QueryTransformationService`) resolving ambiguous pronouns and implicit references into standalone queries using `phi4-mini:latest`.
- [x] Pre-flight query rewrite preview endpoint (`POST /api/v1/projects/{project_id}/chat/rewrite`) and frontend review modal.
- [x] Student control toggle allowing explicit choice between rewritten query and original raw query.
- [x] Multi-query parallel retrieval expanding queries into diverse search angles (`MultiQueryRetriever`).
- [x] Sub-query decomposition splitting compound comparative queries into atomic sub-questions.
- [x] Candidate chunk deduplication by `chunk_id` and cross-encoder reranking against the primary query.
- [x] Redis-backed semantic caching (`RedisSemanticCache`) with vector cosine similarity ($\ge 0.95$) returning answers in sub-70ms on cache hits.
- [x] Request deduplication distributed mutex locks with 15s TTL.
- [x] Database migration `20261003000003_phase8_conversational_rag.sql` adding Phase 8 columns and indexes to `messages`.
- [x] Controlled evaluation experiment on 327-page textbook `DECAP470_CLOUD_COMPUTING.pdf` across 6 conversational scenarios documented in `docs/PHASE_8_CONVERSATIONAL_MULTIQUERY_REPORT.md`.

---

## Phase 9: Metadata Filtering, Dynamic Retrieval Routing, and Adaptive RAG
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
