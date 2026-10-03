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
