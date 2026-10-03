import asyncio
import json
from pathlib import Path
import time
import uuid

from app.core.config import settings
from app.db.session import get_session_factory
from app.rag.pipeline import AdvancedRAGPipeline, BaselineRAGPipeline

QUERIES = [
    {
        "id": "Q1",
        "topic": "NIST Cloud Computing Definition",
        "query": "What is the NIST definition of cloud computing?",
    },
    {
        "id": "Q2",
        "topic": "Type 1 vs Type 2 Hypervisors in Virtualization",
        "query": "What are the differences between Type 1 and Type 2 hypervisors in virtualization?",
    },
    {
        "id": "Q3",
        "topic": "Cloud Service Models (SaaS vs PaaS vs IaaS)",
        "query": "Compare SaaS, PaaS, and IaaS service models",
    },
    {
        "id": "Q4",
        "topic": "Cloud Storage Security Risks & Mitigation",
        "query": "What are the main security risks and mitigation strategies in cloud storage?",
    },
]

WORKSPACE_ID = uuid.UUID("6869b194-56b0-47c9-bb2c-2d373e02706e")
PROJECT_ID = uuid.UUID("a0583e36-c065-43eb-a020-35fb160f5580")
DOCUMENT_ID = uuid.UUID("dcbce759-728f-471f-9233-4f112546fa54")
OUTPUT_PATH = Path("docs/phase_7_experiment_data.json")


async def run_experiment():
    print("=" * 80, flush=True)
    print("STUDYSPACE AI — PHASE 6 vs PHASE 7 CONTROLLED EXPERIMENT", flush=True)
    print(f"Document ID: {DOCUMENT_ID}", flush=True)
    print(f"Workspace: {WORKSPACE_ID}", flush=True)
    print(f"Project: {PROJECT_ID}", flush=True)
    print("=" * 80, flush=True)

    baseline_pipeline = BaselineRAGPipeline()
    advanced_pipeline = AdvancedRAGPipeline()

    comparison_results = []
    # If partial results exist from earlier run, load them to avoid redundant LLM calls if needed
    existing_map = {}
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing_map = {item["id"]: item for item in data}
        except Exception:
            pass

    for item in QUERIES:
        qid = item["id"]
        topic = item["topic"]
        q = item["query"]

        if qid in existing_map:
            print(f"\n[CACHE HIT] Loaded {qid}: {topic} from previous run", flush=True)
            comparison_results.append(existing_map[qid])
            continue

        print(f"\nEvaluating {qid}: {topic}", flush=True)
        print(f"Query: '{q}'", flush=True)

        # 1. Run Baseline (Dense Vector Only)
        print("  -> Running Baseline Vector RAG (top_k=5)...", flush=True)
        b_res = await baseline_pipeline.execute(
            query=q,
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
            top_k=5,
        )
        print(
            f"     Baseline Done: total={b_res.total_latency_ms}ms "
            f"(retrieval={b_res.retrieval_latency_ms}ms, gen={b_res.generation_latency_ms}ms)",
            flush=True,
        )

        # 2. Run Advanced Hybrid (Dense + Lexical + RRF + Reranker)
        print("  -> Running Advanced Hybrid RAG (dense=20, lexical=20, RRF k=60, rerank top=5)...", flush=True)
        a_res = await advanced_pipeline.execute(
            query=q,
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
            dense_top_k=20,
            lexical_top_k=20,
            final_top_k=5,
        )
        print(
            f"     Advanced Done: total={a_res.total_latency_ms}ms "
            f"(dense={a_res.dense_latency_ms}ms, lex={a_res.lexical_latency_ms}ms, "
            f"rrf={a_res.fusion_latency_ms}ms, rerank={a_res.rerank_latency_ms}ms, gen={a_res.generation_latency_ms}ms)",
            flush=True,
        )

        b_chunks = [
            {
                "chunk_index": c.chunk_index,
                "page": c.page_start,
                "heading": c.heading,
                "score": round(c.similarity_score, 4),
            }
            for c in b_res.retrieved_chunks
        ]

        a_chunks = [
            {
                "chunk_index": c.chunk_index,
                "page": c.page_start,
                "heading": c.heading,
                "method": c.retrieval_method,
                "rerank_score": round(c.rerank_score or 0.0, 4),
                "rrf_score": round(c.rrf_score or 0.0, 5),
                "dense_score": round(c.dense_score or 0.0, 4) if c.dense_score else None,
                "lex_score": round(c.lexical_score or 0.0, 4) if c.lexical_score else None,
            }
            for c in a_res.retrieved_chunks
        ]

        entry = {
            "id": qid,
            "topic": topic,
            "query": q,
            "baseline": {
                "total_latency_ms": b_res.total_latency_ms,
                "retrieval_latency_ms": b_res.retrieval_latency_ms,
                "generation_latency_ms": b_res.generation_latency_ms,
                "chunks": b_chunks,
                "citations_count": len(b_res.citations),
                "answer": b_res.answer,
                "tokens": b_res.token_usage,
            },
            "advanced": {
                "total_latency_ms": a_res.total_latency_ms,
                "retrieval_latency_ms": a_res.retrieval_latency_ms,
                "generation_latency_ms": a_res.generation_latency_ms,
                "dense_latency_ms": a_res.dense_latency_ms,
                "lexical_latency_ms": a_res.lexical_latency_ms,
                "fusion_latency_ms": a_res.fusion_latency_ms,
                "rerank_latency_ms": a_res.rerank_latency_ms,
                "dense_candidates": a_res.dense_candidates_count,
                "lexical_candidates": a_res.lexical_candidates_count,
                "fused_candidates": a_res.fused_candidates_count,
                "chunks": a_chunks,
                "citations_count": len(a_res.citations),
                "answer": a_res.answer,
                "tokens": a_res.token_usage,
            },
        }
        comparison_results.append(entry)

        # Incremental save
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(comparison_results, f, indent=2)

    print(f"\n[SUCCESS] Experiment complete. Raw data saved to {OUTPUT_PATH}", flush=True)
    return comparison_results

if __name__ == "__main__":
    asyncio.run(run_experiment())
