# Antigravity Handoff — StudySpace AI

Read `STUDYSPACE_AI_MASTER_ARCHITECTURE.md` completely before proposing changes.

## Your role
Act as the architecture-aware coding agent for StudySpace AI. The master architecture file defines the product scope, UX, architecture boundaries, data model, RAG behaviour, supported formats, security constraints, evaluation requirements, and deployment boundaries.

## Current instruction
At this time, the user is asking to finalize and understand the full structure. **Do not write code or begin building anything yet.** Do not create an implementation plan or phase breakdown. We will discuss the implementation approach separately and authorize it later.

## Requirements you must preserve
- Education-focused document intelligence SaaS named StudySpace AI (working name).
- Students create projects, upload their subject materials, and chat against selected project sources.
- Document target: up to 500 pages per file, with asynchronous ingestion and configurable size/quota/OCR limits.
- Initial formats: PDF, DOCX, PPTX, TXT, MD; do not claim other formats are supported until designed and tested.
- Email/password, Google, and GitHub authentication through Supabase Auth.
- Strict separation of documents, chats, generated resources, exports, and API keys between users.
- React + TypeScript + Vite + Tailwind + shadcn/ui frontend hosted on Vercel.
- Python + FastAPI backend, Supabase PostgreSQL/pgvector and private Storage, separate background worker, and Redis-compatible queue/cache where configured.
- Ollama for local LLM development; Gemini as the initial hosted generation provider through a provider abstraction.
- Configurable embedding provider/model and reranker; never mix incompatible embedding models/dimensions in one vector index.
- Advanced RAG: structure-aware chunking, hybrid lexical+dense retrieval, RRF, reranking, context-aware follow-ups, optional query rewriting with original-query fallback/confirmation, grounded generation, validated citations, and safe semantic caching.
- Project-contained revision checklist with `Not started`, `Learning`, and `Revised` states, linked to sources/chats/study guides.
- Project-contained quizzes: MCQ, short-answer, and difficult questions; hide answer keys/explanations until attempt submission.
- Study guides saved in projects.
- Single-answer and full-conversation exports to PDF/DOCX; 10/15/20-page choices with 20 as maximum and explicit overflow handling.
- Developer API keys: secure hash at rest, shown once, scoped, rate-limited, revocable; provider keys stay server-side.
- LikeC4 architecture views, evaluation metrics, observability, and measured performance comparisons.

## Constraints
- Do not invent that the user's ten subject PDFs have been supplied. They will be provided later for evaluation.
- Do not present synthetic test records as actual user data.
- Do not put secrets into source control or frontend bundles.
- Do not bypass row-level/user ownership checks for convenience.
- Do not represent a document as indexed before ingestion completes.
- Do not assert retrieval/answer quality improvements without benchmark results.
- Do not claim 500-page performance is verified before testing representative documents.
- Do not add unrelated features or change the agreed stack without explicit approval.

For now, acknowledge that you have reviewed the specification, identify any genuine contradictions or missing decisions, and wait for the user's next instruction. Do not implement.
