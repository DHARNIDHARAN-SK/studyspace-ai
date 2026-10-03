import asyncio
import json
from pathlib import Path
import time
from typing import Any, Dict, Optional

from app.core.logging import logger
from app.db.models import Document
from app.db.session import get_session_factory
from app.rag.evaluation.dataset import export_dataset_json, get_evaluation_dataset
from app.rag.evaluation.evaluator import RAGEvaluator
from sqlalchemy import select


async def run_full_benchmark(output_json_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Executes the comprehensive Phase 9 RAG evaluation comparing:
    1. Phase 6 Baseline RAG
    2. Phase 7 Advanced Hybrid RAG (Dense + Lexical tsvector + RRF + Local Passage Reranker)
    3. Phase 8 Conversational RAG (Query Rewriting + Multi-Query + Redis Semantic Cache)
    """
    logger.info("Initializing Phase 9 RAG Evaluation & Benchmarking...")

    # 1. Resolve Document & Tenancy
    async with get_session_factory()() as session:
        doc = await session.scalar(
            select(Document).where(Document.original_filename == "DECAP470_CLOUD_COMPUTING.pdf")
        )
        if not doc:
            raise RuntimeError(
                "Document DECAP470_CLOUD_COMPUTING.pdf not found in database. Ingestion must be completed first."
            )
        workspace_id = doc.workspace_id
        project_id = doc.project_id
        logger.info(
            "Target evaluation document identified: %s (ID: %s, Workspace: %s, Project: %s)",
            doc.original_filename,
            doc.id,
            workspace_id,
            project_id,
        )

    # Export dataset for version control
    dataset_file = Path("docs/decap470_eval_dataset.json")
    export_dataset_json(dataset_file)
    logger.info("Evaluation dataset saved to %s", dataset_file)

    evaluator = RAGEvaluator(workspace_id=workspace_id, project_id=project_id)

    # 2. Evaluate Baseline Pipeline (Phase 6)
    logger.info(">>> Running Phase 6 Baseline RAG Benchmark...")
    baseline_bench = await evaluator.evaluate_pipeline("baseline")

    # 3. Evaluate Advanced Hybrid Pipeline (Phase 7)
    logger.info(">>> Running Phase 7 Advanced Hybrid RAG Benchmark...")
    advanced_bench = await evaluator.evaluate_pipeline("advanced")

    # 4. Evaluate Conversational Pipeline (Phase 8)
    logger.info(">>> Running Phase 8 Conversational / Multi-Query RAG Benchmark (Cold Cache)...")
    conversational_bench = await evaluator.evaluate_pipeline("conversational")

    # 5. Evaluate Cache Performance (Warm Cache Repeat)
    logger.info(">>> Running Phase 8 Warm Cache Repeat Evaluation...")
    warm_cache_results = []
    # Test on first 3 queries
    for item in evaluator.dataset[:3]:
        r = await evaluator.evaluate_item_conversational(item)
        warm_cache_results.append(r)

    warm_cache_hit_rate = sum(1 for r in warm_cache_results if r.cache_hit) / len(warm_cache_results)
    warm_cache_mean_lat = sum(r.total_latency_ms for r in warm_cache_results) / len(warm_cache_results)

    logger.info(
        "Warm Cache Test: Hit Rate = %.1f%%, Mean Latency = %.1fms (vs Cold = %.1fms)",
        warm_cache_hit_rate * 100,
        warm_cache_mean_lat,
        conversational_bench.mean_latency_ms,
    )

    # 6. Assemble Full Benchmark Output
    output_data: Dict[str, Any] = {
        "benchmark_metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "evaluation_document": "DECAP470_CLOUD_COMPUTING.pdf",
            "document_pages": 327,
            "document_chunks": 1728,
            "llm_model": "phi4-mini:latest",
            "embedding_model": "nomic-embed-text:latest",
            "reranker": "Local Deterministic Cross-Feature Reranker (n-gram, coverage, proximity, structure, dense)",
            "lexical_engine": "PostgreSQL tsvector / ts_rank_cd",
            "total_test_queries": len(evaluator.dataset),
        },
        "pipelines": {
            "baseline": baseline_bench.to_dict(),
            "advanced": advanced_bench.to_dict(),
            "conversational": conversational_bench.to_dict(),
        },
        "cache_benchmark": {
            "warm_cache_queries_tested": len(warm_cache_results),
            "warm_cache_hit_rate": round(warm_cache_hit_rate, 4),
            "warm_cache_mean_latency_ms": round(warm_cache_mean_lat, 1),
            "cold_cache_mean_latency_ms": round(conversational_bench.mean_latency_ms, 1),
            "speedup_factor": round(conversational_bench.mean_latency_ms / max(1.0, warm_cache_mean_lat), 2),
        },
        "comparison_summary": {
            "recall_at_5": {
                "baseline": round(baseline_bench.mean_recall_at_k, 4),
                "advanced": round(advanced_bench.mean_recall_at_k, 4),
                "conversational": round(conversational_bench.mean_recall_at_k, 4),
                "delta_advanced_vs_baseline": round(advanced_bench.mean_recall_at_k - baseline_bench.mean_recall_at_k, 4),
                "delta_conversational_vs_advanced": round(conversational_bench.mean_recall_at_k - advanced_bench.mean_recall_at_k, 4),
            },
            "mrr": {
                "baseline": round(baseline_bench.mean_mrr, 4),
                "advanced": round(advanced_bench.mean_mrr, 4),
                "conversational": round(conversational_bench.mean_mrr, 4),
                "delta_advanced_vs_baseline": round(advanced_bench.mean_mrr - baseline_bench.mean_mrr, 4),
            },
            "ndcg": {
                "baseline": round(baseline_bench.mean_ndcg, 4),
                "advanced": round(advanced_bench.mean_ndcg, 4),
                "conversational": round(conversational_bench.mean_ndcg, 4),
                "delta_advanced_vs_baseline": round(advanced_bench.mean_ndcg - baseline_bench.mean_ndcg, 4),
            },
            "context_precision": {
                "baseline": round(baseline_bench.mean_context_precision, 4),
                "advanced": round(advanced_bench.mean_context_precision, 4),
                "conversational": round(conversational_bench.mean_context_precision, 4),
            },
            "context_recall": {
                "baseline": round(baseline_bench.mean_context_recall, 4),
                "advanced": round(advanced_bench.mean_context_recall, 4),
                "conversational": round(conversational_bench.mean_context_recall, 4),
            },
            "faithfulness": {
                "baseline": round(baseline_bench.mean_faithfulness, 4),
                "advanced": round(advanced_bench.mean_faithfulness, 4),
                "conversational": round(conversational_bench.mean_faithfulness, 4),
            },
            "answer_relevance": {
                "baseline": round(baseline_bench.mean_answer_relevance, 4),
                "advanced": round(advanced_bench.mean_answer_relevance, 4),
                "conversational": round(conversational_bench.mean_answer_relevance, 4),
            },
            "latency_p50_ms": {
                "baseline": round(baseline_bench.p50_latency_ms, 1),
                "advanced": round(advanced_bench.p50_latency_ms, 1),
                "conversational": round(conversational_bench.p50_latency_ms, 1),
            },
            "latency_p95_ms": {
                "baseline": round(baseline_bench.p95_latency_ms, 1),
                "advanced": round(advanced_bench.p95_latency_ms, 1),
                "conversational": round(conversational_bench.p95_latency_ms, 1),
            },
        },
    }

    # Save to disk
    out_path = output_json_path or Path("docs/phase9_evaluation_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    logger.info("Comprehensive benchmark results saved to %s", out_path)

    return output_data


if __name__ == "__main__":
    asyncio.run(run_full_benchmark())
