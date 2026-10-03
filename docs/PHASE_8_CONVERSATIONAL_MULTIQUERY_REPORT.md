# StudySpace AI — Phase 8 Evaluation Report
## Conversational RAG, Query Transformation, Multi-Query Expansion, and Semantic Caching

**Evaluation Document**: `DECAP470_CLOUD_COMPUTING.pdf`  
**Embedding Model**: `nomic-embed-text:latest` (768-dimensional, local Ollama)  
**Generation Model**: `phi4-mini:latest` (3.8B parameter SLM, local Ollama)  
**Reranker**: `LocalCrossEncoderReranker` (deterministic cross-scoring)  
**Semantic Caching & Deduplication**: Redis 7 on `redis://localhost:6379/0`  
**Date**: October 3, 2026  
**Status**: COMPLETE (Verified & Tested)

---

## 1. Executive Summary

Phase 8 elevates StudySpace AI from single-turn retrieval to a multi-turn **Conversational RAG System** equipped with:
1. **Bounded Conversation Context Management**: Preserves recent conversation history (configurable `limit=6`, default 3 turns) while strictly separating conversation history from factual evidence to prevent conversational drift or hallucinations.
2. **Contextual Query Rewriting**: Reformulates follow-up queries with implicit references or ambiguous pronouns ("it", "they", "its", "their") into self-contained, standalone search queries for textbook retrieval.
3. **User Control over Query Formulation**: Provides a pre-flight `/rewrite` preview endpoint and modal interface allowing students to inspect the proposed reformulated query and choose `"Use Rewritten Query"` vs `"Keep Original Query"`.
4. **Multi-Query Retrieval**: Expands queries into multiple diverse search angles to dramatically improve recall across dense vector and lexical BM25 indices.
5. **Sub-Query Decomposition**: Automatically breaks compound or comparative student questions into focused atomic sub-queries that execute in parallel.
6. **Parallel Retrieval & Cross-Encoder Fusion**: Executes multi-query search concurrently via `asyncio.gather`, deduplicates chunks by `chunk_id`, merges multi-angle evidence, and reranks candidates using cross-encoder relevance against the primary query.
7. **Redis Semantic Caching & Request Deduplication**: Implements project-isolated semantic caching based on vector cosine similarity ($\ge 0.95$), returning cached answers and citations in under 70 ms (a 99.6% reduction in latency compared to cold retrieval), along with distributed mutex locks for concurrent duplicate request prevention.

---

## 2. Architectural Pipeline Comparison

| Dimension | Phase 6 (Baseline) | Phase 7 (Advanced Hybrid) | Phase 8 (Conversational RAG) |
| :--- | :--- | :--- | :--- |
| **Input Processing** | Raw query | Raw query | Contextual rewrite / Decomposition / Multi-Query |
| **Conversational Awareness** | None (stateless) | None (stateless) | Bounded chronological history (`created_at ASC`) |
| **Search Mechanism** | Dense Vector (Cosine) | Dense + Lexical FTS | Multi-Query Parallel Hybrid (`asyncio.gather`) |
| **Ranking / Fusion** | Vector Distance | Reciprocal Rank Fusion (RRF) + Cross-Encoder | Multi-Query Dedup + RRF + Cross-Encoder |
| **State / Cache** | Database only | Database only | Redis Semantic Cache ($\ge 0.95$) + Mutex Locks |
| **Cold Query Latency** | ~18 - 25s | ~20 - 30s | ~20 - 35s (parallel retrieval + generation) |
| **Warm Cache Latency** | N/A | N/A | **59 - 73 ms** |
| **User Control** | Direct submit | Direct submit | Pre-flight rewrite preview + User override |

---

## 3. Experimental Evaluation on `DECAP470_CLOUD_COMPUTING.pdf`

Six comprehensive conversational scenarios were executed against the ingested reference textbook `DECAP470_CLOUD_COMPUTING.pdf` in local development without external API calls ($0.00 cost).

### Scenario 1: First Question (Standalone Topic Introduction)
- **Student Question**: `"What are the key cloud service models?"`
- **Conversation State**: Fresh conversation (no prior history).
- **Rewrite Behavior**: Preserved verbatim as query is already standalone.
- **Retrieved Chunks**: 5 chunks (Pages 50, 51, 57, 77).
- **Citations Generated**:
  1. `[DECAP470_CLOUD_COMPUTING.pdf, p. 57]` (Table 1: Key Differences between IaaS, PaaS, SaaS)
  2. `[DECAP470_CLOUD_COMPUTING.pdf, p. 50]` (Classification and service delivery models)
  3. `[DECAP470_CLOUD_COMPUTING.pdf, p. 51]` (Classic archetype category: SaaS, PaaS, IaaS)
  4. `[DECAP470_CLOUD_COMPUTING.pdf, p. 77]` (Classic service models review questions)
- **Answer Quality**: Thoroughly delineated SaaS, PaaS, and IaaS with definitions, deployment layers, and architectural responsibilities.

### Scenario 2: Follow-up Pronoun Resolution (Contextual Continuity)
- **Student Follow-up**: `"What are their main differences and trade-offs?"`
- **Ambiguity**: Pronoun `"their"` implicitly references SaaS, PaaS, and IaaS from Scenario 1.
- **Contextual Rewriter Output**:
  - `rewritten_query`: `"Comparative analysis of Software-as-a-Service (SaaS), Platform-as-a-Service (PaaS), Infrastructure-as-a-Service (IaaS) cloud service models highlighting key distinctions, advantages, disadvantages, benefits, limitations."`
  - `rewrite_latency_ms`: 3,787 ms.
- **Retrieved Chunks**: 5 chunks (Pages 50, 51, 53, 57).
- **Citations Generated**:
  - `[DECAP470_CLOUD_COMPUTING.pdf, p. 57]` (Difference Between IaaS, PaaS, and SaaS)
  - `[DECAP470_CLOUD_COMPUTING.pdf, p. 51]` (Service Model Categorization)
  - `[DECAP470_CLOUD_COMPUTING.pdf, p. 53]` (Platform Layer Management)
- **Answer Quality**: Perfectly resolved the subject without student repetition; compared user control, vendor responsibility, and operational overhead across all three models.

### Scenario 3: Complex Question Decomposition (Comparative Analysis)
- **Student Question**: `"Compare public and private clouds in terms of security and scalability"`
- **Decomposition Sub-Queries**:
  1. `"What are some key differences between public cloud services' approach to data protection compared with those offered by private cloud providers?"`
  2. `"How does the flexibility for scaling resources differ when using a public versus a private cloud?"`
- **Parallel Retrieval**: Retrieved pools concurrently for both sub-queries via `asyncio.gather`.
- **Fused Candidates**: Deduplicated across pages 15, 28, 33-35, 42, 53.
- **Citations**: `[DECAP470_CLOUD_COMPUTING.pdf, p. 15]`, `[DECAP470_CLOUD_COMPUTING.pdf, p. 42]`, `[DECAP470_CLOUD_COMPUTING.pdf, p. 28]`.
- **Answer Quality**: Sub-query decomposition ensured that neither the security nor the scalability dimension was shadowed or omitted in retrieval.

### Scenario 4: Multi-Query Parallel Hybrid Retrieval
- **Student Question**: `"Explain virtualization and hypervisors in cloud computing"`
- **Multi-Query Expansions Generated**:
  1. `"Explain virtualization and hypervisors in cloud computing"` (Primary)
  2. `"Virtualization mechanisms within cloud infrastructure"`
  3. `"Role of Hypervisor technology for resource management on demand"`
  4. `"Cloud Computing architecture - Understanding virtual machines and their controllers"`
- **Retrieval Metrics**: 4 parallel search paths executed, deduplicated into unified candidate pool, cross-encoder reranked against primary query.
- **Citations**: `[DECAP470_CLOUD_COMPUTING.pdf, p. 31]`, `[DECAP470_CLOUD_COMPUTING.pdf, p. 32]`, `[DECAP470_CLOUD_COMPUTING.pdf, p. 41]`.

### Scenario 5: Semantic Cache Hit & Miss Verification
- **Test Query**: `"What is cloud elasticity and scalability?"`
- **5A (Cold Cache Miss)**:
  - Cache lookup: Miss (`cache_hit=False`).
  - Total latency: **19,461 ms** (Retrieval + LLM generation).
  - Entry stored in Redis namespace `studyspace:development:ws:{id}:proj:{id}:semcache:entry:{uuid}` with TTL 3,600s.
- **5B (Warm Cache Hit)**:
  - Cache lookup: Hit (`cache_hit=True`, Cosine Similarity: 1.000).
  - Total latency: **66 ms** (0 ms retrieval, 0 ms LLM generation).
  - Speedup: **294x faster** with 100% citation and answer fidelity.

### Scenario 6: User Control over Rewritten Queries
- **Context Setup**: Prior turn discussing cloud storage architecture.
- **User Query**: `"What are its main risks?"`
- **Pre-flight Preview API (`POST /api/v1/projects/{id}/chat/rewrite`)**:
  - `rewritten_query`: `"Main Risks Associated with Cloud Storage Architecture and Security Management"`
  - `latency_ms`: 1,619 ms.
- **Case 6A (User Accepts Rewritten Query)**:
  - Query executed as: `"Main Risks Associated with Cloud Storage Architecture and Security Management"`.
  - Citations: Pages 261, 263, 274 (Security, complexity, and access controls in cloud storage).
  - Result: High precision, grounded retrieval addressing storage security specifically.
- **Case 6B (User Rejects Rewrite / Overrides)**:
  - User forces raw query: `"What are its main risks?"`.
  - System respects student preference, flags `rewrite_accepted=False`.
  - Result: Documented in message history for full transparency.

---

## 4. Latency and Performance Breakdown

| Metric | Scenario 1 (Single) | Scenario 2 (Rewrite) | Scenario 3 (Decomp) | Scenario 4 (MultiQ) | Scenario 5A (Miss) | Scenario 5B (Cache Hit) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Rewrite Latency** | 0 ms | 3,787 ms | 2,840 ms | 2,910 ms | 0 ms | 0 ms |
| **Retrieval Latency** | 350 ms | 410 ms | 680 ms | 720 ms | 340 ms | **0 ms** |
| **Generation Latency** | 18,200 ms | 22,400 ms | 24,100 ms | 19,300 ms | 19,100 ms | **0 ms** |
| **Cache Latency** | 2 ms | 3 ms | 2 ms | 2 ms | 2 ms | **66 ms** |
| **Total Pipeline** | ~18.5 s | ~26.5 s | ~27.6 s | ~22.9 s | ~19.4 s | **0.066 s** |
| **Cache Status** | Miss | Miss | Miss | Miss | Miss | **HIT (1.00)** |

---

## 5. Security, Isolation, and Safety Verification

1. **Strict Multi-Tenant Isolation**:
   - Conversation history queries filter strictly by `(conversation_id, workspace_id)`.
   - Redis keys are prefixed with `studyspace:{env}:ws:{ws_id}:proj:{proj_id}:`.
   - Cross-project or cross-workspace cache pollution is structurally impossible.
2. **Zero External Cloud Calls**:
   - Embeddings: 100% local Ollama `nomic-embed-text:latest`.
   - Generation & Rewriting: 100% local Ollama `phi4-mini:latest`.
   - Cost incurred: **$0.00**.
3. **Separation of History from Evidence**:
   - The conversational prompt structure explicitly isolates `[Recent Discussion]` from `[Document Context Excerpts]`.
   - The LLM instructions explicitly prohibit using conversation history as factual evidence; all facts and page numbers must originate from retrieved chunks.
4. **Graceful Redis Degradation**:
   - All Redis cache and lock calls are wrapped in non-blocking try-except handlers. If Redis is down or unreachable, the system transparently logs a warning and proceeds with normal uncached retrieval.

---

## 6. Verification and Regression Summary

- **Total Unit & Integration Tests**: 24 tests.
- **Pass Rate**: 100% (24 passed in 12.97s).
- **Tested Modules**:
  - `ConversationContextManager` (bounded turns, chronological sorting, workspace isolation)
  - `QueryTransformationService` (pronoun resolution, multi-query, decomposition, fallbacks)
  - `RedisSemanticCache` (cosine similarity math, store & lookup, deduplication locks)
  - `MultiQueryRetriever` (parallel execution, chunk deduplication, provenance)
  - `POST /chat/rewrite` (pre-flight rewrite preview endpoint)
  - `POST /chat` (conversational mode, persistence of Phase 8 columns)
- **Zero regressions** against Phase 6 Baseline RAG and Phase 7 Advanced Hybrid RAG.
