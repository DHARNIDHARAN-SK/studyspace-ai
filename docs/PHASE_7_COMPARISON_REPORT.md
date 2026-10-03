# StudySpace AI — Phase 7 Controlled Comparison Report
## Baseline Vector RAG (Phase 6) vs. Advanced Hybrid RAG (Phase 7)

**Document Evaluated:** `D:\RAG_DATA_TESTING\DECAP470_CLOUD_COMPUTING.pdf`  
**File Size:** 13,573,276 bytes | **Total Pages:** 327 | **Indexed Chunks:** 1,728  
**Models:** Local Ollama `nomic-embed-text:latest` (768d, HNSW cosine) + `phi4-mini:latest` (temperature 0.1)  
**External Cloud Calls:** Exactly 0 (100% offline local inference)

---

## 1. Executive Summary

Phase 7 successfully introduced **Advanced Hybrid Retrieval** combining:
1. **Dense Vector Search** using PostgreSQL `pgvector` with HNSW cosine distance indexing (`nomic-embed-text:latest`, 768 dimensions).
2. **Lexical Full-Text Search (BM25 Equivalent)** using PostgreSQL `tsvector` with weighted GIN indexing ('A' for headings, 'B' for body text) and length-normalized ranking (`ts_rank_cd` with normalization flag 32).
3. **Reciprocal Rank Fusion (RRF)** fusing dense candidates ($top\_k=20$) and lexical candidates ($top\_k=20$) with configurable smoothing ($k=60$).
4. **Local Cross-Encoder Reranker** evaluating term coverage, exact n-gram matching, token span proximity, structural heading relevance, and dense similarity into a calibrated score without requiring external model weights or downloads.

---

## 2. Quantitative Performance & Benchmark Comparison

| Query ID | Topic | Pipeline Mode | Retrieval Latency | Generation Latency | Total Latency | Retrieved Candidates | Top Chunk #1 Heading | Top Chunk Provenance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Q1** | NIST Cloud Computing Definition | **Baseline (Dense)** | 250 ms | 18,182 ms | 18,432 ms | 5 | 2.7 Cloud Business Models | `dense` |
| **Q1** | NIST Cloud Computing Definition | **Advanced (Hybrid)** | **94 ms** | **5,202 ms** | **5,296 ms** | **37 fused** | Unit 02: Cloud Architecture | `reranked` (hybrid) |
| **Q2** | Type 1 vs Type 2 Hypervisors | **Baseline (Dense)** | 87 ms | 23,429 ms | 23,516 ms | 5 | Unit 11: Virtual Machine | `dense` |
| **Q2** | Type 1 vs Type 2 Hypervisors | **Advanced (Hybrid)** | 122 ms | **22,012 ms** | **22,134 ms** | **32 fused** | Unit 11: Virtual Machine | `reranked` (hybrid) |
| **Q3** | SaaS vs PaaS vs IaaS Models | **Baseline (Dense)** | 86 ms | 35,836 ms | 35,923 ms | 5 | Unit 03: Cloud Services | `dense` |
| **Q3** | SaaS vs PaaS vs IaaS Models | **Advanced (Hybrid)** | 135 ms | **18,672 ms** | **18,807 ms** | **32 fused** | Unit 03: Cloud Services | `reranked` (hybrid) |
| **Q4** | Cloud Storage Security & Risks | **Baseline (Dense)** | 87 ms | 31,610 ms | 31,697 ms | 5 | 12.2 Security Challenges | `dense` |
| **Q4** | Cloud Storage Security & Risks | **Advanced (Hybrid)** | 108 ms | 35,194 ms | 35,302 ms | **38 fused** | Unit 12: Security & Standards | `reranked` (hybrid) |

---

## 3. Key Qualitative Observations & Retrieval Provenance

### Query 1: "What is the NIST definition of cloud computing?"
- **Baseline RAG:** Retrieved dense chunks around general business models (p. 39) and intro (p. 20).
- **Advanced Hybrid RAG:** Concurrently pulled 20 dense and 20 lexical candidates, resulting in 37 unique candidates. Chunk 248 ("Unit 02: Cloud Computing Architecture and Models", p. 45) matched in both streams (`dense_score: 0.7298`, `lex_score: 0.898`, `RRF: 0.02674`, `rerank_score: 0.7974`).
- **Grounded Verification:** Both pipelines correctly recognized that while NIST goals and references appear in the course book, the literal formalized NIST SP 800-145 definition text was not excerpted, properly avoiding hallucinations.

### Query 2: "What are the differences between Type 1 and Type 2 hypervisors in virtualization?"
- **Baseline RAG:** Retrieved 5 chunks solely by vector similarity. Chunks 1171 (Pros of Virtualization) and 1237 were retrieved, while Chunk 1271 ("11.4 Hypervisors") was omitted.
- **Advanced Hybrid RAG:** 3 of the top 5 chunks were dual-matched (`reranked`). Lexical search retrieved Chunk 1271 ("11.4 Hypervisors", p. 244) which vector search had missed. Reranker elevated Chunk 1277 (p. 247, Score: 0.7505) and Chunk 1274 (p. 245, Score: 0.7297) to the top positions, giving concrete definitions and architectural diagrams of bare-metal vs hosted hypervisors.

### Query 3: "Compare SaaS, PaaS, and IaaS service models"
- **Baseline RAG:** Retrieved general service chunks with significant generation latency (35.8s).
- **Advanced Hybrid RAG:** Fused 32 candidates. 4 out of 5 top chunks were retrieved by both dense and lexical search (Chunks 304, 305, 415, 283). Reranking concentrated context on Unit 03 ("Cloud Services", pp. 53-77), reducing generation latency to 18.6s and producing a clear comparison table.

### Query 4: "What are the main security risks and mitigation strategies in cloud storage?"
- **Baseline RAG:** Retrieved chunks exclusively from Section 12.1 and 12.2.
- **Advanced Hybrid RAG:** Fused 38 candidates from Chapter 2 (Issues in Cloud Computing, p. 27) and Chapter 12 (Security and Standards, pp. 261-274). Chunk 1425 (Page 274) was elevated to rank #1 due to high lexical and dense agreement (`dense_score: 0.7174`, `lex_score: 0.8889`, `rerank_score: 0.6974`).

---

## 4. Architectural Verification

1. **Multi-Tenant Isolation:** Verified across `workspace_id` and `project_id`. Unauthorized cross-project queries return 0 chunks or 403 Forbidden.
2. **Local Model Safety:** `LocalCrossEncoderReranker` is 100% deterministic and runs in pure Python with zero external model weights. If an uninstalled library is requested, `RerankerModelNotFoundError` is raised without pulling anything silently.
3. **Pipeline Switch:** Supported via `RAG_RETRIEVAL_MODE=baseline|advanced` configuration in `.env` and per-query request parameter `mode="baseline"|"advanced"`.
