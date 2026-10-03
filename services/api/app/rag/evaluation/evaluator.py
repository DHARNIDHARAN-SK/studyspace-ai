import time
from typing import Dict, List, Optional
import uuid

from app.core.logging import logger
from app.rag.conversation.context_manager import ConversationTurn
from app.rag.evaluation.dataset import get_evaluation_dataset
from app.rag.evaluation.metrics import (
    calculate_answer_relevance,
    calculate_context_precision,
    calculate_context_recall,
    calculate_faithfulness,
    calculate_mrr,
    calculate_ndcg,
    calculate_percentile,
    calculate_recall_at_k,
)
from app.rag.evaluation.models import (
    EvaluationItem,
    ItemEvaluationResult,
    PipelineBenchmarkResult,
)
from app.rag.pipeline import (
    AdvancedRAGPipeline,
    BaselineRAGPipeline,
    ConversationalRAGPipeline,
)


class RAGEvaluator:
    """
    Automated, reproducible evaluator for StudySpace AI RAG subsystems.
    Runs controlled experiments comparing Baseline, Advanced, and Conversational pipelines.
    """

    def __init__(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        dataset: Optional[List[EvaluationItem]] = None,
    ):
        self.workspace_id = workspace_id
        self.project_id = project_id
        self.dataset = dataset or get_evaluation_dataset()

        self.baseline_pipeline = BaselineRAGPipeline()
        self.advanced_pipeline = AdvancedRAGPipeline()
        self.conversational_pipeline = ConversationalRAGPipeline()

    async def evaluate_item_baseline(self, item: EvaluationItem) -> ItemEvaluationResult:
        """Executes and scores an evaluation item against Phase 6 Baseline RAG."""
        res = await self.baseline_pipeline.execute(
            query=item.query,
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            top_k=5,
        )

        retrieved_context = " ".join(c.content for c in res.retrieved_chunks)
        retrieved_pages = [c.page_start or 0 for c in res.retrieved_chunks]

        recall = calculate_recall_at_k(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords, k=5)
        mrr = calculate_mrr(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords)
        ndcg = calculate_ndcg(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords, k=5)
        precision = calculate_context_precision(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords)
        c_recall = calculate_context_recall(retrieved_context, item.ground_truth_answer, item.ground_truth_keywords)
        faith = calculate_faithfulness(res.answer, retrieved_context)
        relevance = calculate_answer_relevance(res.answer, item.query, item.ground_truth_answer)

        token_count = (res.token_usage.get("prompt_tokens", 0) or 0) + (res.token_usage.get("completion_tokens", 0) or 0)

        return ItemEvaluationResult(
            item_id=item.id,
            query=item.query,
            category=item.category,
            generated_answer=res.answer,
            retrieved_chunk_count=len(res.retrieved_chunks),
            retrieved_pages=retrieved_pages,
            recall_at_k=recall,
            mrr=mrr,
            ndcg=ndcg,
            context_precision=precision,
            context_recall=c_recall,
            faithfulness=faith,
            answer_relevance=relevance,
            total_latency_ms=res.total_latency_ms,
            retrieval_latency_ms=res.retrieval_latency_ms,
            generation_latency_ms=res.generation_latency_ms,
            cache_hit=False,
            token_count=token_count,
            inference_count=1,
        )

    async def evaluate_item_advanced(self, item: EvaluationItem) -> ItemEvaluationResult:
        """Executes and scores an evaluation item against Phase 7 Advanced Hybrid RAG."""
        res = await self.advanced_pipeline.execute(
            query=item.query,
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            dense_top_k=20,
            lexical_top_k=20,
            final_top_k=5,
        )

        retrieved_context = " ".join(c.content for c in res.retrieved_chunks)
        retrieved_pages = [c.page_start or 0 for c in res.retrieved_chunks]

        recall = calculate_recall_at_k(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords, k=5)
        mrr = calculate_mrr(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords)
        ndcg = calculate_ndcg(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords, k=5)
        precision = calculate_context_precision(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords)
        c_recall = calculate_context_recall(retrieved_context, item.ground_truth_answer, item.ground_truth_keywords)
        faith = calculate_faithfulness(res.answer, retrieved_context)
        relevance = calculate_answer_relevance(res.answer, item.query, item.ground_truth_answer)

        token_count = (res.token_usage.get("prompt_tokens", 0) or 0) + (res.token_usage.get("completion_tokens", 0) or 0)

        return ItemEvaluationResult(
            item_id=item.id,
            query=item.query,
            category=item.category,
            generated_answer=res.answer,
            retrieved_chunk_count=len(res.retrieved_chunks),
            retrieved_pages=retrieved_pages,
            recall_at_k=recall,
            mrr=mrr,
            ndcg=ndcg,
            context_precision=precision,
            context_recall=c_recall,
            faithfulness=faith,
            answer_relevance=relevance,
            total_latency_ms=res.total_latency_ms,
            retrieval_latency_ms=res.retrieval_latency_ms,
            generation_latency_ms=res.generation_latency_ms,
            cache_hit=False,
            token_count=token_count,
            inference_count=1,
        )

    async def evaluate_item_conversational(self, item: EvaluationItem, allow_cache: bool = True) -> ItemEvaluationResult:
        """Executes and scores an evaluation item against Phase 8 Conversational / Multi-Query RAG."""
        history_turns = [
            ConversationTurn(role=h["role"], content=h["content"])
            for h in item.history
        ]

        res = await self.conversational_pipeline.execute(
            query=item.query,
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            history=history_turns,
            rewrite_enabled=True,
            multi_query_enabled=True,
            decomposition_enabled=True,
            final_top_k=5,
        )

        retrieved_context = " ".join(c.content for c in res.retrieved_chunks)
        retrieved_pages = [c.page_start or 0 for c in res.retrieved_chunks]

        recall = calculate_recall_at_k(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords, k=5)
        mrr = calculate_mrr(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords)
        ndcg = calculate_ndcg(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords, k=5)
        precision = calculate_context_precision(res.retrieved_chunks, item.relevant_page_start, item.relevant_page_end, item.ground_truth_keywords)
        c_recall = calculate_context_recall(retrieved_context, item.ground_truth_answer, item.ground_truth_keywords)
        faith = calculate_faithfulness(res.answer, retrieved_context)
        relevance = calculate_answer_relevance(res.answer, item.query, item.ground_truth_answer)

        token_count = (res.token_usage.get("prompt_tokens", 0) or 0) + (res.token_usage.get("completion_tokens", 0) or 0)
        # Inferences: 1 generation + 1 rewrite/multiquery if enabled and not cache hit
        inference_count = 0 if res.cache_hit else (2 if (res.rewrite_enabled or res.multi_query_enabled) else 1)

        return ItemEvaluationResult(
            item_id=item.id,
            query=item.query,
            category=item.category,
            generated_answer=res.answer,
            retrieved_chunk_count=len(res.retrieved_chunks),
            retrieved_pages=retrieved_pages,
            recall_at_k=recall,
            mrr=mrr,
            ndcg=ndcg,
            context_precision=precision,
            context_recall=c_recall,
            faithfulness=faith,
            answer_relevance=relevance,
            total_latency_ms=res.total_latency_ms,
            retrieval_latency_ms=res.retrieval_latency_ms,
            generation_latency_ms=res.generation_latency_ms,
            cache_hit=res.cache_hit,
            token_count=token_count,
            inference_count=inference_count,
        )

    async def evaluate_pipeline(self, mode: str) -> PipelineBenchmarkResult:
        """Runs the entire benchmark dataset through the specified pipeline mode."""
        logger.info("Starting RAG evaluation benchmark for mode=%s on %d items", mode, len(self.dataset))
        item_results: List[ItemEvaluationResult] = []

        for idx, item in enumerate(self.dataset, 1):
            logger.info("Evaluating [%s/%d] (ID: %s, Category: %s)...", idx, len(self.dataset), item.id, item.category)
            if mode == "baseline":
                r = await self.evaluate_item_baseline(item)
            elif mode == "advanced":
                r = await self.evaluate_item_advanced(item)
            elif mode == "conversational":
                r = await self.evaluate_item_conversational(item)
            else:
                raise ValueError(f"Unknown evaluation pipeline mode: {mode}")

            item_results.append(r)

        # Aggregate statistics
        total = len(item_results)
        latencies = [float(r.total_latency_ms) for r in item_results]

        res = PipelineBenchmarkResult(
            pipeline_name=f"Phase {6 if mode=='baseline' else 7 if mode=='advanced' else 8} {mode.capitalize()} RAG",
            retrieval_mode=mode,
            total_queries=total,
            mean_recall_at_k=sum(r.recall_at_k for r in item_results) / total,
            mean_mrr=sum(r.mrr for r in item_results) / total,
            mean_ndcg=sum(r.ndcg for r in item_results) / total,
            mean_context_precision=sum(r.context_precision for r in item_results) / total,
            mean_context_recall=sum(r.context_recall for r in item_results) / total,
            mean_faithfulness=sum(r.faithfulness for r in item_results) / total,
            mean_answer_relevance=sum(r.answer_relevance for r in item_results) / total,
            mean_latency_ms=sum(latencies) / total,
            p50_latency_ms=calculate_percentile(latencies, 50.0),
            p95_latency_ms=calculate_percentile(latencies, 95.0),
            mean_retrieval_latency_ms=sum(r.retrieval_latency_ms for r in item_results) / total,
            mean_generation_latency_ms=sum(r.generation_latency_ms for r in item_results) / total,
            cache_hit_rate=sum(1 for r in item_results if r.cache_hit) / total,
            total_inferences=sum(r.inference_count for r in item_results),
            total_tokens=sum(r.token_count for r in item_results),
            item_results=item_results,
        )

        logger.info(
            "Benchmark completed for mode=%s: Recall@5=%.3f, MRR=%.3f, nDCG=%.3f, Faith=%.3f, p50_latency=%.1fms",
            mode,
            res.mean_recall_at_k,
            res.mean_mrr,
            res.mean_ndcg,
            res.mean_faithfulness,
            res.p50_latency_ms,
        )
        return res
