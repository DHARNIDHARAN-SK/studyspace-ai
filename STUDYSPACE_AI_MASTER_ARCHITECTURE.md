# StudySpace AI — Master Product & System Architecture

**Document type:** Product requirements and technical architecture specification  
**Status:** Architecture baseline for review  
**Product name:** StudySpace AI (working name; branding can change)  
**Primary audience:** Students and independent learners  
**Secondary audience:** Developers integrating StudySpace AI through its REST API  
**Primary document target:** Support an individual uploaded document of up to 500 pages, subject to configurable file-size, extraction, OCR, quota, and infrastructure limits.  
**Important:** This document defines what the product should be and how its components fit together. It is not a coding task list. Do not start implementation until the user separately authorizes it.

---

## 1. Product definition

StudySpace AI is a multi-tenant, education-focused document intelligence SaaS. Students create projects for subjects, upload their own academic materials, ask questions grounded in those sources, revisit conversations, export study materials, track revision progress, and generate quizzes. Developers can optionally use a secured platform API to add document-grounded question answering to their own applications.

### 1.1 Problem being solved

Students often keep lecture notes, textbooks, presentations, research papers, questions, and revision notes in separate places. They must manually search long files, lose the context of previous questions, and recreate summaries or study resources. StudySpace AI brings source-grounded chat and learning tools into one persistent, private workspace.

### 1.2 Core user value

- Upload study materials and ask questions in natural language.
- Receive answers grounded in the student's selected source documents, with verifiable citations.
- Organize materials and conversations by subject/project.
- Reopen old conversations without losing context.
- Export an individual answer or a complete conversation to PDF or Word.
- Track revision topics and practice with quizzes generated from the student's sources.
- Optionally access the same RAG capability through a platform API key.

### 1.3 Product principles

1. **Evidence first:** the system must distinguish source-backed answers from general model knowledge and admit when the selected sources do not contain enough evidence.
2. **Private by default:** users must never retrieve another user's documents, chunks, chats, quizzes, exports, or cached answers.
3. **One project, persistent context:** sources and learning resources belong to a project and can be reused across conversations in that project.
4. **Measured quality:** retrieval and answer-generation changes are evaluated against a fixed dataset rather than assumed to improve performance.
5. **Responsive and understandable:** show document-processing status, clear errors, and citations a student can inspect.
6. **Provider independence:** LLM, embedding, and reranking integrations must be behind provider interfaces so models can be swapped without rewriting application logic.
7. **No fake analytics:** usage and quality dashboards must show measured values only; unavailable metrics should be labelled as unavailable, not fabricated.

### 1.4 Out of scope for the initial product

- Training a foundation model from scratch.
- Treating the application as a substitute for teachers, medical/legal professionals, or authoritative textbooks.
- Automatic web search as a hidden source for answers. The initial RAG scope uses the user's selected project documents.
- Shared team workspaces and complex organization administration unless explicitly added later.
- Advertising support for a file format before its parser, source references, errors, and tests are defined.

---

## 2. Product modes

### 2.1 Student mode

The core application experience:

- Create a subject/project.
- Upload files to that project.
- Wait for document indexing to complete.
- Start one or more conversations over all project sources or selected sources.
- Inspect citations and source passages.
- Generate quizzes and study guides.
- Maintain a revision checklist.
- Export responses or conversations.

### 2.2 Developer API mode

A developer creates a platform API key, associates the key with a permitted workspace/project, and calls StudySpace AI's REST API. The backend authenticates the platform key, checks its scope and quota, executes the same retrieval pipeline, and returns a structured answer and citations.

Platform API keys are **not** Gemini keys or Ollama credentials. The developer's key authenticates requests to StudySpace AI; the server's model-provider credentials remain private on the server.

---

## 3. Supported document formats and 500-page target

### 3.1 Initial supported formats

Only show a format as supported in the upload UI after its full ingestion and citation path has been tested.

| Extension | Format | Extraction and citation metadata |
|---|---|---|
| `.pdf` | PDF | Text, page number, headings where recoverable, page-level source location |
| `.docx` | Microsoft Word Open XML | Paragraphs, headings, tables where supported, heading/section and paragraph reference |
| `.pptx` | PowerPoint Open XML | Slide text, title, slide number, speaker notes only if explicitly enabled |
| `.txt` | Plain text | Text and character/line offsets where available |
| `.md` | Markdown | Headings, sections, code blocks, and section path |

### 3.2 Later-format candidates

CSV/XLSX, legacy `.doc`/`.ppt`, HTML, images, audio, and other formats are not part of the initial supported list unless separately approved. Spreadsheet support needs table-aware retrieval and row/sheet provenance. Scanned PDFs and image-only files require OCR and need their own quality and resource limits.

### 3.3 Maximum document size

The design target is **up to 500 pages per document**, not a promise that any 500-page file can be processed regardless of size or quality. The application must also enforce configurable byte-size, page-count, extracted-text, OCR, token, storage, and account-quota limits.

Required behaviour for large files:

- Upload to private object storage; do not send an entire large file through a long-lived chat request.
- Create an asynchronous ingestion job and return a job/document ID quickly.
- Extract and process pages in bounded batches; do not load the entire extracted corpus into memory unnecessarily.
- Batch embedding requests and apply bounded concurrency and retry/backoff.
- Display progress states such as `Uploaded`, `Queued`, `Extracting`, `OCR processing` (when applicable), `Chunking`, `Embedding`, `Indexed`, `Failed`, and `Needs attention`.
- Permit retry after recoverable failure and make ingestion idempotent so a retry does not create duplicate chunks.
- Store page/slide/section provenance on every chunk so answers can cite original locations.
- Never pass all 500 pages to the LLM as one prompt. The query pipeline retrieves a small, relevant evidence set within a configured context budget.
- If a document exceeds a configured limit or contains unsupported/encrypted/corrupt content, explain the actual reason and how the user can resolve it.
- If the PDF is scanned, detect low text extraction and use a separate OCR path only if OCR is enabled and within the user's limits. Clearly report OCR failure or partial extraction.

### 3.4 Multiple uploaded documents

A project may contain multiple documents. The system must support the user's planned evaluation corpus of approximately 10 subject-related PDFs when they are supplied later. Those test files must be user-provided; do not fabricate their contents or show them as real documents in production UI. Indexing several large PDFs must be queued and rate-limited rather than performed simultaneously without bounds.

---

## 4. UI and navigation architecture

Use a responsive, calm, professional education SaaS design. The primary workspace should be visually quiet and content-focused: light neutral surfaces, readable typography, one restrained accent colour, consistent spacing, accessible contrast, subtle borders, clear loading/empty/error states, and minimal animation.

Design-reference workflow: study interaction patterns in Mobbin and SaaSUI; explore layouts with v0; implement the selected system with React, Tailwind CSS, and shadcn/ui. These are references/tools, not runtime dependencies.

### 4.1 Public website

#### Page 1 — Landing page

Contains:
- Brand and concise value proposition.
- Primary calls to action: `Get started` and `Sign in`.
- Product preview focused on project sources and grounded chat.
- Core feature sections: chat with notes, citations, projects, revision checklist, quiz generation, PDF/Word export, and developer API.
- Supported-format list that matches tested parser capability.
- How it works section.
- About, Contact, Privacy, Terms, and footer links.
- Contact email/contact form only when a real destination and support process are configured. Never invent a phone number, email, customer count, testimonial, or company address.

#### Public About and Contact views

These can be separate routes or sections, but must be reachable from the public navigation/footer. Contact form submissions need server-side validation and spam protection.

### 4.2 Authentication

#### Page 2 — Sign in / Sign up

- Email + password registration and sign-in.
- Google OAuth.
- GitHub OAuth.
- Email verification and password reset.
- Terms and privacy links.
- Clear provider error and cancellation handling.

Use Supabase Auth. OAuth credentials and redirect URLs must be configured in the relevant provider dashboard and Supabase settings. Do not store raw passwords in the application database.

### 4.3 Authenticated app shell

Use a persistent left sidebar on desktop and a drawer on mobile. Main navigation:

- Home / Dashboard
- Projects
- Search conversations
- Pinned conversations
- Developer API (may be under a Developer section)
- Settings
- Profile/account menu

The user should be able to access recent chats and projects from the sidebar without switching to a separate history screen for every action.

#### Page 3 — Student dashboard

Contains:
- A concise greeting and `Create project` action.
- Recent projects.
- Recent conversations and pinned chats.
- Recently opened learning resources.
- Document processing activity and failures requiring attention.
- Empty state for first-time users, with a clear first-project/upload action.
- Real data only; never seed production usage charts with fake activity.

#### Page 4 — Projects list

Each project card contains project name, optional description/subject, source count, conversation count, last activity, and menu actions. Support search, sorting, rename, archive, and delete confirmation. Project creation should be a small accessible dialog.

#### Page 5 — Project workspace (core page)

This is the main experience. It contains:

**Project header**
- Project name and rename action.
- Source count and project menu.
- Tabs or secondary navigation for `Chat`, `Sources`, `Revision`, `Quizzes`, and `Study guides`.

**Chat sidebar**
- New chat.
- Search conversations.
- Pinned chats.
- Recent conversations.
- Conversation rename, pin/unpin, archive, and delete actions.
- Chat titles may be suggested from the first user query but must remain editable.

**Conversation canvas**
- User and assistant messages.
- Clear streaming/loading/error state.
- Code blocks, tables, headings, and formatted lists.
- Answer actions: copy, regenerate, feedback, download response, and inspect citations.
- Source citations linked to a specific document/page/slide/section when available.
- Preserve the original user question even when a rewritten query is used internally.

**Composer**
- Text input and send action.
- Project/source selector to use all project sources or a chosen subset.
- Query-rewriting control.
- Optional attachment/upload entry point, subject to the current project's ingestion workflow.
- Clearly show if selected documents are still processing and not yet searchable.

**Sources panel**
- Collapsible panel/drawer listing project files, format, page count when available, upload date, processing status, and actions.
- Open source, rename, retry indexing, remove from project, and delete according to permissions.
- Do not imply a document is ready for retrieval before indexing finishes.
- In citations, show the source passage and original page/slide/section metadata. If a viewer is unavailable, show the quoted passage and location instead of a broken link.

Use a responsive layout: collapse sidebars into drawers on narrow screens. Do not force three wide columns onto mobile.

#### Page 6 — Conversation history

- Searchable conversation list.
- Filter by project and date.
- Reopen a saved conversation with messages and its project association intact.
- Pin, rename, archive, and delete.
- Reopened chat uses its authorized project/source scope, subject to source availability and permission checks.
- If the source document was deleted, preserve the conversation but make it clear that the old citation/source is no longer available.

#### Page 7 — Developer API

- Create a named platform API key.
- Display the full key only once at creation; store only a secure hash server-side.
- Revoke and rotate keys.
- Scope keys to a workspace/project and allowed capabilities.
- Show creation date, last-used timestamp, status, permitted scope, rate/quota information, and request logs.
- Show OpenAPI/API documentation and copyable code examples.
- Never show or expose server-side Gemini or other provider credentials.

#### Page 8 — Settings and profile

- Display name and account information.
- Connected identity provider(s).
- Security/session controls where supported.
- Theme preference (light/dark only if both are implemented consistently).
- Data export and account deletion requests.
- Privacy and retention information.
- Usage/quota information when enabled.

### 4.4 Learning tools inside each project

Do not create unrelated top-level applications for learning tools. They belong within the project workspace and use that project's source content.

#### Revision checklist

Each topic contains:
- Topic name and optional description.
- Status: `Not started`, `Learning`, or `Revised`.
- Links to relevant source document/page/section.
- Links to relevant conversations.
- Links to generated study guides.
- Optional personal notes and last-updated timestamp.
- Search, filter by status, and progress summary.

Checklist topics can be created manually or suggested from uploaded material. AI-suggested items must be editable and must cite their source context. Status changes must persist per user/project.

#### Quiz generator

Generate questions from selected project sources and let students choose:
- Multiple-choice questions.
- Short-answer questions.
- Difficult/challenge questions.
- Number of questions and, where suitable, topic/source scope.

Question records need the prompt, question type, options when applicable, expected answer, explanation, source references, and difficulty label. The expected answer and explanation must not be revealed before the student attempts/submits the question. For MCQs, reveal the correct option and explanation after submission; for short answers, provide a model answer and feedback after submission. Persist attempts and results so students can review prior quizzes. The model must not invent a source citation for a question that is not grounded in the selected material.

#### Study guides

Generate source-grounded revision notes, summaries, definitions, formula sheets, and key-concept lists. Save each study guide inside its project with the source references used. Allow reopening and exporting it. Do not present a guide as complete if the generation or source extraction failed.

### 4.5 Answer and conversation export

Support exports in:
- PDF.
- Word `.docx`.

**Single-response export:** include the associated question, assistant response, headings, tables, code blocks where supported, and source references. Source citations should retain document and page/slide/section information.

**Full-conversation export:** include the user and assistant messages in order. Optional settings may include timestamps and source citations. Add title, project name, generated date, page numbering, and readable print styles.

Maximum full-conversation export length: configurable options of 10, 15, or 20 pages, with 20 pages as the maximum. If the transcript will exceed the selected cap, do not silently label a truncated document as complete. Offer one or more of:
- Create a clearly labelled condensed export preserving every question and essential answer points.
- Export a selected date range or selected messages.
- Download multiple parts if that option is later chosen.

PDF output must have consistent pagination and no clipped tables/code. DOCX must be editable. Generation should occur server-side or in a controlled export worker for reliable rendering. Protect exports with the same ownership rules as the original conversation. Temporary export files should expire according to a configurable retention policy.

### 4.5.1 Query rewriting UX

Query rewriting is a user-controlled retrieval setting. When disabled, retrieve using the original query. When enabled:

1. Use the relevant conversation history to propose a standalone retrieval query when needed.
2. Show the original and proposed query when user confirmation is enabled.
3. Provide `Use rewritten query` and `Use original query` choices.
4. If the user rejects the rewrite, retrieve using the exact original query.
5. Keep the original user message unchanged in conversation history.
6. If rewriting errors or times out, fall back safely to the original query and record the failure in telemetry.

Do not force a rewrite for every simple, self-contained query. Query rewriting must be evaluated because it can increase latency and occasionally distort intent.

---

## 5. High-level system architecture

### 5.1 Main components

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui; hosted on Vercel.
- **Authentication:** Supabase Auth for email/password, Google OAuth, and GitHub OAuth.
- **API/backend:** Python + FastAPI in a persistent service.
- **Database:** Supabase PostgreSQL; pgvector for dense embeddings; PostgreSQL full-text search for lexical retrieval.
- **File storage:** private Supabase Storage bucket(s) for original files and, if needed, generated exports.
- **Background processing:** Celery workers for ingestion and longer jobs; Redis-compatible managed broker/backend. Workers run separately from Vercel frontend functions.
- **LLM provider:** Ollama for local development; Gemini API for the hosted configuration, behind a provider abstraction.
- **Embedding provider:** configured via provider abstraction; each active vector index is tied to one specific embedding model/version and vector dimension.
- **Reranker:** configurable cross-encoder or hosted reranking provider; optional fallback when unavailable.
- **Cache/rate limiting:** Redis where configured; cache keys must include authorization scope and relevant versions.
- **Evaluation and observability:** structured logs, traces, RAG evaluations, latency, error, cost/token, and cache metrics.
- **Architecture documentation:** LikeC4 diagrams embedded in an Architecture page. Diagrams should mirror the real architecture, not imply nonexistent runtime features.

### 5.2 Deployment boundary

Vercel hosts the web UI and may host only small, short-lived frontend-oriented functions. The Python API and persistent Celery workers run on a suitable persistent service (for example, a container host). Supabase provides managed auth, PostgreSQL/pgvector, and object storage. Redis is a separate managed service where needed.

Ollama is local-development only by default. Never expose an unrestricted local Ollama endpoint publicly. Hosted inference uses the configured Gemini provider or another explicitly configured provider.

### 5.3 Architecture views to document with LikeC4

- System context: student/developer, web application, API, Supabase, model provider.
- Container/component view: frontend, FastAPI, ingestion worker, retrieval engine, provider adapters, database, storage, Redis.
- Ingestion sequence: upload → validate/store → queue → extract/OCR → chunk → embed → index → indexed status.
- Query sequence: auth → query settings/context → retrieval → fusion → rerank → evidence validation → generation → citation validation → response.
- Developer API sequence: platform-key authentication → scope/quota enforcement → same RAG service → response.
- Deployment view: Vercel, backend service, worker, Supabase, Redis, model providers.

---

## 6. Document ingestion architecture

### 6.1 Ingestion flow

1. Authenticate the user and verify project ownership.
2. Validate file extension, MIME type, actual file signature, byte size, page count where cheaply available, and account quota.
3. Store the original file in a private bucket using a non-guessable storage path.
4. Create a document record with status `uploaded` or `queued` and enqueue an idempotent job.
5. Parse content with a format-specific parser.
6. For PDFs, assess text extraction quality. If the file appears scanned and OCR is enabled, route it to a bounded OCR workflow.
7. Normalize text while preserving useful structure and source locations.
8. Split into structure-aware chunks with controlled overlap.
9. Attach metadata to each chunk.
10. Generate embeddings in batches using the configured embedding model.
11. Store text, metadata, searchable representation, and vector.
12. Verify the indexing result and mark the document `indexed` only when the required stages succeed.
13. Notify the UI through polling or a supported status-update channel.

### 6.2 Chunking requirements

Use structure-aware chunking rather than a single fixed-size split for every format. Preserve:
- Document ID and title.
- Project/workspace/user scope.
- Page start/end for PDF.
- Slide number/title for PPTX.
- Heading/section path for DOCX/Markdown.
- Chunk index and content hash.
- Parser version and extraction metadata.
- Embedding model/version used.

Initial chunk size, overlap, and batch size must be configurable. Select initial values through evaluation on the real student document corpus. Avoid splitting a heading from the paragraph it introduces when feasible. Keep table/list content understandable and attach adjacent heading context where useful.

### 6.3 Idempotency, update, deletion

- Use a checksum to identify exact re-uploads within an authorized scope.
- Re-indexing must not produce duplicated chunk sets.
- Updating/replacing a document should mark the old version and update the searchable index atomically or through a safe version-switch process.
- Deleting a document must remove it from retrieval immediately, then delete chunks/embeddings and stored content according to retention rules.
- If a project/source changes while a conversation exists, old citations should remain descriptive but may be marked unavailable if the source was deleted.

---

## 7. Advanced RAG query architecture

### 7.1 Query pipeline

1. **Authentication and scope:** authenticate Supabase session or platform API key. Resolve workspace, project, and permitted document set before retrieving anything.
2. **Query/context preparation:** load a bounded amount of relevant conversation history. Keep the original user question immutable.
3. **Optional query rewrite:** if enabled, generate a standalone search query and follow the configured accept/original flow.
4. **Parallel retrieval:** run dense vector search and lexical/full-text retrieval over only the authorized selected sources.
5. **Rank fusion:** use Reciprocal Rank Fusion (RRF) or a measured alternative to combine result lists.
6. **Reranking:** rerank a bounded candidate pool with the configured reranker.
7. **Diversity and deduplication:** remove near-duplicate chunks and optionally apply a measured diversity strategy (such as MMR) to reduce repetitive context.
8. **Evidence filtering:** reject weak or irrelevant evidence based on calibrated retrieval scores/rules. Thresholds must be evaluated rather than guessed.
9. **Context assembly:** build a context within the configured model token budget. Include source IDs and location metadata with each evidence passage.
10. **Grounded generation:** instruct the model to answer from supplied evidence, distinguish inference from explicit source statements, and say when the evidence is insufficient.
11. **Citation validation:** verify that cited chunk/document IDs exist in the retrieved set and that displayed page/slide/section metadata comes from stored metadata, not generated model text.
12. **Response persistence:** save user message, assistant response, provider/model details, source links, retrieval trace metadata, and timing data subject to privacy/retention settings.
13. **Feedback and metrics:** accept helpful/not-helpful feedback and record non-sensitive evaluation metrics.

### 7.2 Hybrid retrieval

Dense vector retrieval helps with semantic similarity; lexical retrieval helps with exact phrases, technical terms, variable names, formulas, and course-specific vocabulary. Combine them rather than assuming one method is sufficient.

Candidate count, final `top_k`, lexical/vector weights (if used), fusion settings, and reranker cutoff must be configurable and benchmarked. Ensure every database search enforces workspace/project/document authorization. Filters are not optional.

### 7.3 Context-aware follow-up questions

For a follow-up such as “What are its limitations?”, use recent relevant history to identify what “it” refers to and construct a standalone retrieval query. Avoid forwarding the complete conversation. Use a bounded history window or a compact summary with clear source/message references. The original query remains the user-visible message.

### 7.4 Grounded answer behaviour

The generation prompt must require the model to:
- Use retrieved evidence for claims about the uploaded material.
- Cite the supplied source IDs in a format the backend can validate.
- Avoid fabricating quotes, source titles, pages, or citations.
- Say that the selected sources do not provide enough information when evidence is insufficient.
- Separate a source statement from an explanation/inference where relevant.
- Avoid following instructions embedded in retrieved documents that attempt to override system policy, disclose secrets, or access other users' data.
- Treat uploaded documents as untrusted content, not instructions to the RAG system.

### 7.5 Semantic caching

Semantic caching is optional and must not compromise privacy or correctness. Only consider a cache hit after checking:
- The same authorization scope/workspace/project.
- The same or equivalent selected document set and document versions.
- Compatible model, prompt, retrieval, and index configuration versions.
- Similarity threshold validated against false-hit tests.
- No user-specific/private context mismatch.

Store cache metadata sufficient to invalidate entries on document changes, project changes, model/config changes, or key revocation. Do not cache secrets. Record cache hits/misses and validate cached-answer quality. If safe equivalence is uncertain, bypass the cache.

---

## 8. Models and provider configuration

### 8.1 Provider abstraction

Use distinct interfaces/adapters for:
- Chat/generation model.
- Embedding model.
- Query-rewrite model/function.
- Reranker.
- OCR/parser provider where applicable.

Application business logic must not contain model-specific request formats throughout the codebase. Provider adapters normalize inputs, outputs, errors, token usage where available, timeouts, and retries.

### 8.2 Development and hosted settings

**Local development:** Ollama is the default generation provider. The actual installed model is configured by environment variable; do not hardcode a model name across the application. Embeddings may use a compatible local embedding model.

**Hosted deployment:** Gemini is the initial hosted generation provider, configured on the backend. Embeddings and reranking must be configured independently; they do not have to use the same vendor as generation.

**Important embedding consistency rule:** vectors created by different embedding models or different vector dimensions must not be mixed in the same index. Persist provider/model/version and dimension metadata. Changing the embedding model requires a re-embedding/re-indexing process or a separate versioned index. Keep local and hosted indexes separate unless the exact same embedding model/version and preprocessing are used.

### 8.3 Model settings to expose to administrators/configuration

- `LLM_PROVIDER` (for example, `ollama` or `gemini`).
- `OLLAMA_BASE_URL` (local/private endpoint only).
- `OLLAMA_CHAT_MODEL`.
- `GEMINI_API_KEY` (server secret).
- `GEMINI_CHAT_MODEL` (configurable model ID).
- `EMBEDDING_PROVIDER`.
- `EMBEDDING_MODEL_ID`.
- `EMBEDDING_VECTOR_DIMENSIONS` (must match the selected model and database schema).
- `RERANKER_PROVIDER` (`local`, `remote`, or `disabled`).
- `RERANKER_MODEL_ID` and provider credential where required.
- `MAX_CONTEXT_TOKENS`, generation token limit, temperature, timeout, retry policy, and concurrency.

These are server-side settings. Students should not be shown raw provider secrets. An administrator may see safe provider status and non-secret model names.

### 8.4 Provider failure handling

- Set timeouts and bounded retries with exponential backoff/jitter for transient provider errors.
- Respect provider rate limits and retry-after responses when available.
- Do not retry deterministic validation errors indefinitely.
- If a provider fails, return a clear recoverable error; do not fabricate an answer.
- Use a fallback model only when explicitly configured and safe for the task.
- Record which provider/model served an answer so evaluations can be compared later.

---

## 9. RAG evaluation and performance optimization

The product should be able to compare techniques and configuration variants using the same evaluation dataset. Do not claim that one method is better until measurements support it.

### 9.1 Evaluation dataset

Use a versioned dataset containing:
- Test question.
- Authorized source document(s).
- Expected answer or key facts.
- Expected supporting chunk/page/section where possible.
- Question category (factual, multi-step, exact phrase, formula, follow-up, insufficient evidence, etc.).
- Expected abstention for questions not answerable from selected sources.

The initial real-world dataset will be based on the user's approximately 10 subject-specific PDFs when provided later. Until those files are provided, use clearly marked synthetic fixtures only for software tests; never represent fixtures as the user's real study documents.

### 9.2 Retrieval measurements

Track where applicable:
- Recall@k.
- Precision@k.
- Mean Reciprocal Rank (MRR).
- nDCG@k.
- Evidence coverage/correct source retrieval.

### 9.3 Generation measurements

Track where applicable:
- Faithfulness/groundedness.
- Answer relevance.
- Correctness against reference answers or instructor-reviewed criteria.
- Citation precision and citation completeness.
- Abstention correctness for insufficient-evidence questions.

Automated metrics are signals, not a guarantee of correctness. Keep a human-review path for a sample of generated answers and questions.

### 9.4 Performance and operating metrics

- End-to-end latency: p50 and p95.
- Ingestion duration by file size/page count and parser/OCR path.
- Time spent in rewrite, lexical retrieval, vector retrieval, fusion, reranking, and generation.
- Embedding and generation token/usage cost where available.
- Provider error/rate-limit rate.
- Cache hit rate and semantic false-hit findings.
- Worker queue length, retry count, and failed jobs.
- User/API-key request counts and rate-limit events.

### 9.5 Experiments to compare

- Fixed-size versus structure-aware chunking.
- Dense retrieval versus lexical retrieval versus hybrid retrieval.
- RRF settings and candidate counts.
- Reranking enabled versus disabled.
- Query rewrite enabled versus disabled, with rewrite acceptance/original comparison.
- Context-aware follow-up retrieval versus original-query retrieval.
- Semantic cache disabled versus enabled.
- Local Ollama versus hosted Gemini generation, evaluated separately from retrieval changes.
- Different generation prompt/context budgets.

Report quality and latency together. A technique that improves relevance but increases latency should show both values. Never populate the dashboard with invented scores.

---

## 10. Database and data model

Use PostgreSQL as the system of record. PostgreSQL/pgvector and PostgreSQL full-text search support the initial vector and lexical indexes.

The following is the logical entity model; exact SQL types and embedding dimensions must match the selected providers and migrations.

### 10.1 Core entities

**profiles**
- `id` (matches Supabase Auth user ID).
- `display_name`, `avatar_url` where appropriate.
- `created_at`, `updated_at`.

**workspaces**
- `id`, `owner_user_id`, `name`, `created_at`, `updated_at`.
- Initially, each student has a personal workspace. The schema can permit future membership expansion, but shared team workspaces are not required for the initial product.

**projects**
- `id`, `workspace_id`, `name`, `description`, `subject`, `created_at`, `updated_at`, `archived_at`.

**documents**
- `id`, `workspace_id`, `project_id`, `uploaded_by_user_id`.
- `original_filename`, `storage_path`, `mime_type`, `extension`, `byte_size`, `page_count`.
- `checksum`, `document_version`, `ingestion_status`, `ingestion_error_code`, safe `ingestion_error_message`.
- `parser_name`, `parser_version`, `created_at`, `updated_at`, `indexed_at`, `deleted_at`.

**document_chunks**
- `id`, `workspace_id`, `project_id`, `document_id`, `document_version`, `chunk_index`.
- `content`, `token_count`, `content_hash`.
- `page_start`, `page_end`, `slide_number`, `slide_title`, `section_path`, `heading`, `source_offsets` as applicable.
- `search_vector` for PostgreSQL lexical retrieval.
- `embedding` in a vector column whose dimensions match the selected embedding model.
- `embedding_provider`, `embedding_model_id`, `embedding_model_version`, `created_at`.

**conversations**
- `id`, `workspace_id`, `project_id`, `user_id`, `title`, `is_pinned`, `status`, `created_at`, `updated_at`, `archived_at`.

**messages**
- `id`, `conversation_id`, `workspace_id`, `role`, `content`, `original_user_query` where relevant, `rewritten_query` where enabled and retained.
- `provider`, `model_id`, `prompt_version`, `token_usage` where available, `latency_ms`, `created_at`.

**message_citations**
- `id`, `message_id`, `chunk_id`, `document_id`, source-location snapshot, citation order, and validation status.
- Use a source-location snapshot so the old answer can display the original location even if the source later changes, while marking deleted sources unavailable.

**revision_items**
- `id`, `workspace_id`, `project_id`, `user_id`, `title`, `description`, `status` (`not_started`, `learning`, `revised`), `notes`, `created_at`, `updated_at`.

**revision_item_links**
- Link revision items to documents/chunks, conversations/messages, and study guides.

**quizzes**
- `id`, `workspace_id`, `project_id`, `created_by_user_id`, `title`, source scope, question settings, status, timestamps.

**quiz_questions**
- `id`, `quiz_id`, `question_type`, `difficulty`, `prompt`, options JSON where applicable, protected `expected_answer`, protected `explanation`, source citations, `position`.
- The API must not send `expected_answer` or `explanation` to the client before attempt submission.

**quiz_attempts** and **quiz_responses**
- Store user attempt, submitted answer, correctness/feedback after submission, attempt time, and result. Access must be scoped to the owning user/workspace.

**study_guides**
- `id`, `workspace_id`, `project_id`, `created_by_user_id`, `title`, `content`, guide type, source citations, model/prompt metadata, timestamps.

**exports**
- `id`, `workspace_id`, `user_id`, source entity/conversation ID, format (`pdf` or `docx`), status, private storage path, page count, expiry time, error status, created time.

**api_keys**
- `id`, `workspace_id`, optional `project_id`, `created_by_user_id`, `name`, `key_prefix`, `key_hash`, `scopes`, `rate_limit_policy`, `status`, `last_used_at`, `expires_at`, `created_at`, `revoked_at`.
- Store only the hash of the secret. Never store the raw key after creation.

**usage_events**
- Workspace/API key, event type, model/provider, token/usage counts when available, latency, success/error class, timestamp. Avoid logging full private document content or secrets.

**ingestion_jobs** (or durable task records associated with Celery)
- `id`, document ID/version, job type, status, attempt count, stage, progress metadata, started/finished timestamps, sanitized error code/message.

### 10.2 Indexes and consistency

- Index foreign keys and commonly filtered workspace/project/user columns.
- Add vector index appropriate to the chosen pgvector index strategy and dataset size.
- Add PostgreSQL full-text index for lexical retrieval.
- Add indexes for conversation update time, pinned status, document ingestion status, API key prefix/lookup metadata, and job status.
- Do not create a vector index until embedding dimension and similarity metric are explicitly fixed.
- Keep workspace/project ownership consistent across related rows; use constraints and server-side checks.
- Perform migrations with a consistent migration tool and keep schema changes versioned.

### 10.3 Multi-tenant isolation

Every user-owned query, row, file path, retrieval result, cache entry, export, revision item, quiz, and API-key operation must be scoped to the authenticated user/workspace. Enforce authorization in the backend and, where applicable, PostgreSQL Row Level Security. Never trust `user_id`, `workspace_id`, or `project_id` sent by the frontend without resolving and checking ownership from the authenticated principal.

---

## 11. API architecture

Use versioned REST routes under `/api/v1` for the first-party application and `/v1` (or another explicitly documented versioned prefix) for external developer clients. Keep route conventions consistent and document them with OpenAPI.

### 11.1 First-party authenticated endpoints

Representative endpoint groups:

- `/api/v1/me` — profile/account context.
- `/api/v1/projects` — list/create projects.
- `/api/v1/projects/{project_id}` — retrieve/update/archive/delete project.
- `/api/v1/projects/{project_id}/documents` — list and register uploads.
- `/api/v1/documents/{document_id}` — status, metadata, retry, delete.
- `/api/v1/documents/{document_id}/download` — authorized short-lived download URL where permitted.
- `/api/v1/projects/{project_id}/conversations` — create/list conversations.
- `/api/v1/conversations/{conversation_id}` — retrieve/rename/archive/delete.
- `/api/v1/conversations/{conversation_id}/messages` — submit query and retrieve messages.
- `/api/v1/messages/{message_id}/feedback` — message feedback.
- `/api/v1/messages/{message_id}/export` — export one response.
- `/api/v1/conversations/{conversation_id}/export` — export transcript.
- `/api/v1/projects/{project_id}/revision-items` — CRUD checklist items and links.
- `/api/v1/projects/{project_id}/quizzes` — create/list quiz.
- `/api/v1/quizzes/{quiz_id}/questions` — return questions without answer keys.
- `/api/v1/quizzes/{quiz_id}/attempts` — submit responses and reveal feedback after submission.
- `/api/v1/projects/{project_id}/study-guides` — create/list/get/export study guides.
- `/api/v1/api-keys` — create/list/revoke/rotate platform keys.
- `/api/v1/usage` — authorized usage summary.

This is a logical endpoint inventory, not a request to implement endpoints now. Request/response schemas, pagination, validation, error codes, and idempotency must be documented for actual endpoints.

### 11.2 External developer API

Representative routes:

- `POST /v1/chat/completions` or `POST /v1/query` — submit a question against an authorized project/source scope.
- `GET /v1/projects/{project_id}/documents` — list permitted document metadata if the API-key scope permits it.
- `GET /v1/requests/{request_id}` — retrieve processing/query status only if asynchronous query handling is enabled and authorized.

A request should specify the project and question, and may specify permitted document IDs and retrieval options. The server derives the workspace and authorization scope from the API key; it must not trust a caller-supplied workspace ID without verifying the key's permissions.

Response structure should include:
- `request_id`.
- `answer`.
- `sources`: document ID/title, page/slide/section location, excerpt where permitted, and citation identifier.
- `model`/provider metadata only where safe and useful.
- usage/latency metadata where enabled.
- structured error object for failures.

### 11.3 API-key requirements

- Generate high-entropy random secrets with a recognizable non-secret prefix.
- Display the full secret once only.
- Store a cryptographic hash; compare securely.
- Support key names, scope, project/workspace binding, last-used time, quota, rotation, expiry where configured, and immediate revocation.
- Apply per-key and per-workspace rate limits and request/body size limits.
- Never accept platform keys in URLs/query strings; use an Authorization header.
- Never log full keys or secrets.
- Make revocation invalidate cached authorization decisions promptly.

---

## 12. Security, privacy, and abuse controls

- Use Supabase Auth for identity; keep provider secrets and service-role credentials server-side only.
- Never expose a Supabase service-role key, Gemini key, Redis credential, or private storage credential in browser code.
- Configure private storage buckets and short-lived signed URLs for authorized access.
- Validate file extension, MIME type, file signature, byte size, page count, archive/decompression risks, and parser errors.
- Use malware scanning where supported by the deployment/security requirements.
- Protect against cross-user/project IDOR by checking ownership on every endpoint and retrieval query.
- Use database RLS for exposed user-owned tables and review service-role access carefully; service-role server code must still enforce ownership.
- Apply CSRF/CORS/session protections appropriate to the chosen authentication flow, secure HTTP, and secure cookie/token handling.
- Limit uploads, chat concurrency, request sizes, export jobs, quiz generation, and model usage per user/workspace/key.
- Treat document text as untrusted data. Prompt injection inside uploaded materials must not change system policy or grant tool access.
- Do not execute code or macros from uploaded files.
- Do not include private document content in ordinary logs, tracing metadata, or analytics by default.
- Define retention/deletion policies for original files, chunks, caches, exports, logs, and account deletion.
- Clear or invalidate relevant cache entries after source deletion, project deletion, key revocation, and access changes.
- Include a clear privacy notice and explain which external model provider processes content in the hosted configuration.

---

## 13. Background work, Redis, and scalability

### 13.1 Use a worker for long-running tasks

Document extraction, OCR, embedding batches, re-indexing, large quiz generation, and PDF/DOCX exports can take longer than a normal web request. Queue these jobs and process them in a separate worker process. The frontend should poll a status endpoint or use an explicitly supported status-update mechanism.

### 13.2 Redis responsibilities

Redis is justified for:
- Celery task broker/result backend where configured.
- Rate-limit counters or short-lived coordination.
- Optional semantic cache or safe exact-query cache.

PostgreSQL remains the durable source of truth for users, projects, documents, chunks, conversations, quizzes, checklist items, exports, API keys, and usage records. Do not rely on Redis as the only storage for durable product data.

### 13.3 Scalability rules

- Keep the FastAPI service stateless where possible.
- Scale API replicas separately from ingestion workers.
- Bound worker concurrency and embedding/reranking parallelism.
- Use batch processing and backpressure rather than processing every large document at once.
- Put limits on upload bytes, pages, total project storage, queued jobs, and generation usage.
- Use connection pooling carefully for PostgreSQL.
- Monitor queue depth, worker health, database connections, retrieval latency, and provider limits.
- Keep all provider calls behind timeouts and concurrency controls.
- Treat 500 pages as an ingestion workload target; query-time context is always limited to selected relevant chunks.

---

## 14. Repository / codebase structure target

The eventual repository should use a clear monorepo layout so the frontend, API, worker, shared contracts, documentation, and infrastructure can be tested and deployed separately. Exact file creation is intentionally not prescribed here.

```text
studyspace-ai/
├── apps/
│   └── web/                         # React + Vite + TypeScript frontend
│       ├── public/
│       └── src/
│           ├── app/                 # router, providers, route guards
│           ├── pages/               # landing, auth, dashboard, project workspace
│           ├── components/          # shared UI and product components
│           ├── features/
│           │   ├── auth/
│           │   ├── projects/
│           │   ├── documents/
│           │   ├── chat/
│           │   ├── citations/
│           │   ├── revision/
│           │   ├── quizzes/
│           │   ├── study-guides/
│           │   ├── exports/
│           │   ├── developer-api/
│           │   └── settings/
│           ├── lib/                 # API client, Supabase client, helpers
│           ├── hooks/
│           ├── styles/
│           └── types/
├── services/
│   └── api/                         # FastAPI app and domain services
│       ├── app/
│       │   ├── main.py
│       │   ├── api/                 # versioned route handlers
│       │   ├── core/                # settings, auth, logging, errors
│       │   ├── db/                  # sessions, models, migrations
│       │   ├── schemas/              # request/response validation
│       │   ├── domains/
│       │   │   ├── users/
│       │   │   ├── projects/
│       │   │   ├── documents/
│       │   │   ├── conversations/
│       │   │   ├── revision/
│       │   │   ├── quizzes/
│       │   │   ├── study_guides/
│       │   │   ├── exports/
│       │   │   ├── api_keys/
│       │   │   └── usage/
│       │   ├── rag/
│       │   │   ├── ingestion/
│       │   │   ├── parsing/
│       │   │   ├── chunking/
│       │   │   ├── embeddings/
│       │   │   ├── retrieval/
│       │   │   ├── fusion/
│       │   │   ├── reranking/
│       │   │   ├── rewriting/
│       │   │   ├── context/
│       │   │   ├── generation/
│       │   │   ├── citations/
│       │   │   └── evaluation/
│       │   ├── providers/            # Ollama, Gemini, embeddings, reranker
│       │   ├── workers/              # Celery task definitions
│       │   └── observability/
│       └── tests/
├── packages/
│   └── contracts/                   # OpenAPI-generated/shared API types
├── infra/
│   ├── docker/                      # container definitions
│   ├── compose/                     # local services
│   └── deployment/                  # environment/deployment notes
├── architecture/
│   ├── likec4/                      # source diagrams and views
│   └── decisions/                   # architecture decision records
├── docs/
│   ├── product-spec.md
│   ├── architecture.md
│   ├── security.md
│   ├── rag-evaluation.md
│   └── api.md
├── .env.example                     # placeholder names only; no secrets
├── README.md
└── package/pyproject configuration files
```

The tree is a target separation of responsibilities, not a requirement to create every folder immediately. Avoid premature empty abstractions; retain the boundaries so the application can grow without mixing frontend, RAG, persistence, and provider logic.

---

## 15. Configuration and secret inventory

Provide `.env.example` containing names and safe placeholder values only. Real secrets must never be committed.

### Frontend-safe configuration

- Public Supabase project URL.
- Supabase publishable/anon key, subject to RLS and intended browser use.
- Public API base URL.
- Optional public product configuration.

### Backend-only configuration

- Database connection string or pooler URL.
- Supabase service-role credentials only if needed by trusted server tasks.
- Supabase storage configuration.
- `LLM_PROVIDER`, Ollama URL/model, Gemini API key/model.
- Embedding provider/model/dimension.
- Reranker provider/model/credentials.
- Redis/broker URL and credentials.
- Signing, session, encryption, or application secrets as required.
- Upload byte/page/storage limits and retention windows.
- Worker concurrency, retry count, timeout, batch size.
- Retrieval top-k, RRF settings, reranker cutoff, context token budget, rewrite toggle default.
- Rate limits and quota settings.
- Logging/observability credentials.

Validate required environment configuration at application startup. Do not print secrets in logs, exceptions, telemetry, or frontend build artifacts.

---

## 16. Error states and user feedback

The UI and API must define clear, non-sensitive error handling for:
- Unsupported format.
- File too large or too many pages.
- Encrypted/corrupt file.
- PDF text extraction produced no useful text.
- OCR unavailable, failed, or partially successful.
- Ingestion job queued, delayed, retried, or failed.
- Document still processing and therefore not searchable.
- No relevant evidence found.
- LLM provider timeout, quota/rate limit, or service outage.
- Reranker unavailable with configured fallback behaviour.
- API key invalid, revoked, expired, or over quota.
- Unauthorized project/document access.
- Export exceeds selected page limit.
- Quiz generation incomplete or source evidence insufficient.

Expose a safe error code and useful next action. Do not show stack traces, database errors, secret values, private filesystem paths, or provider credentials to end users.

---

## 17. Acceptance criteria for the product architecture

These are product-level criteria, not an implementation schedule.

### User and data isolation
- Separate users can sign up/sign in by email/password, Google, and GitHub once OAuth is configured.
- A user can only view their own projects, documents, chats, quizzes, checklist items, guides, exports, and API keys.
- Every search path and cache lookup enforces the same ownership scope.

### Document handling
- The upload interface advertises only supported formats.
- A document up to the configured 500-page ceiling is processed asynchronously subject to byte-size, OCR, quota, and infrastructure limits.
- The system preserves source location metadata through parsing, chunking, retrieval, answers, and exports.
- A document is not marked indexed until the searchable index is ready.
- Failed ingestion can be retried without duplicating indexed chunks.

### RAG answers
- Users can chat against all project sources or a selected subset.
- Hybrid retrieval can combine lexical and dense search; candidates can be fused and reranked.
- Follow-up queries can use bounded conversation context.
- Query rewriting can be turned off; when enabled with confirmation, users can accept a rewrite or keep the original.
- Citations only reference retrieved/validated source records.
- Insufficient evidence produces an explicit limitation rather than a fabricated source-backed answer.

### Learning tools
- Checklist status changes persist and items can link to sources, chats, and study guides.
- Quiz answers/explanations are not exposed before the attempt submission.
- Quiz attempts/results can be reviewed by the owning student.
- Study guides are saved in their project and can be exported.

### Export
- Individual responses and full conversations can be exported to PDF and DOCX.
- Full-conversation length options are 10, 15, or 20 pages, maximum 20.
- Export overflow is handled explicitly; no silent truncation.
- Exports are private and protected by the same authorization as their source conversation.

### Developer API
- Platform API keys are hashed at rest, shown once, scoped, rate-limited, and revocable.
- External callers cannot choose another workspace outside the key's authorization.
- API responses include source citations and a request identifier.
- Provider secrets are not exposed to clients.

### Measurement
- Retrieval and generation can be evaluated separately.
- Latency, errors, queue health, token/usage information, and cache metrics are measurable.
- Performance dashboards show measured values only.

---

## 18. Decisions that must remain explicit

These choices should be made deliberately during later technical planning rather than guessed implicitly by the coding agent:

1. Exact embedding model/provider and vector dimension for each environment.
2. Exact generation model ID for Ollama and Gemini deployments.
3. Exact reranker and whether it runs locally or through a hosted service.
4. File byte-size, storage quota, OCR page, and account usage limits.
5. Initial chunk size/overlap, retrieval candidate counts, RRF parameters, reranking cutoff, and context token budget after benchmarking.
6. Whether query-rewrite confirmation is always shown or can be configured by user preference.
7. Export page-count policy for condensed transcripts and whether split exports are supported.
8. Data retention and account deletion windows.
9. The actual public contact details and final brand name.

Do not silently choose production values for these decisions without recording them in configuration/documentation.

---

## 19. Coding-agent guardrails

When this specification is supplied to Antigravity:

- Treat this file as the product and architecture source of truth.
- Do not start coding, create application files, run migrations, install packages, deploy services, or make external account changes merely because this specification was provided.
- Do not create an implementation-phase plan in this document.
- Do not replace the agreed stack or product scope without asking the user.
- Do not invent test PDFs, fake users, fake analytics, fake testimonials, or real-looking production records. Synthetic fixtures must be marked as test data.
- Do not hardcode provider secrets or expose server-side keys in frontend code.
- Do not bypass authorization to make a demo easier.
- Do not claim the 500-page target is proven until tested with real representative documents, including text PDFs and scanned PDFs if OCR is supported.
- Preserve model/provider interfaces, measurable evaluation, citations, multi-tenant isolation, export requirements, and the two learning tools.
- Ask the user before resolving any product decision in Section 18 that materially affects cost, data safety, model selection, or user experience.

**End of master architecture specification.**
