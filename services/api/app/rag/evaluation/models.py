from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationItem:
    """A ground-truth question-answer pair grounded in DECAP470_CLOUD_COMPUTING.pdf."""
    id: str
    category: str  # "fact_lookup", "concept_explanation", "comparative_analysis", "conversational_followup"
    query: str
    ground_truth_answer: str
    relevant_page_start: int
    relevant_page_end: int
    ground_truth_keywords: List[str]
    ground_truth_section: str
    history: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ItemEvaluationResult:
    """Evaluation metrics for a single query processed through a specific pipeline."""
    item_id: str
    query: str
    category: str
    generated_answer: str
    retrieved_chunk_count: int
    retrieved_pages: List[int]

    # Retrieval Metrics
    recall_at_k: float
    mrr: float
    ndcg: float

    # Context Metrics
    context_precision: float
    context_recall: float

    # Answer Quality Metrics
    faithfulness: float
    answer_relevance: float

    # System & Performance Metrics
    total_latency_ms: int
    retrieval_latency_ms: int
    generation_latency_ms: int
    cache_hit: bool = False
    token_count: int = 0
    inference_count: int = 1


@dataclass
class PipelineBenchmarkResult:
    """Aggregated benchmark metrics across the entire evaluation dataset for a pipeline."""
    pipeline_name: str
    retrieval_mode: str
    total_queries: int

    # Mean Retrieval Metrics
    mean_recall_at_k: float
    mean_mrr: float
    mean_ndcg: float

    # Mean Context Metrics
    mean_context_precision: float
    mean_context_recall: float

    # Mean Answer Quality Metrics
    mean_faithfulness: float
    mean_answer_relevance: float

    # Latency Metrics
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    mean_retrieval_latency_ms: float
    mean_generation_latency_ms: float

    # Efficiency Metrics
    cache_hit_rate: float
    total_inferences: int
    total_tokens: int

    item_results: List[ItemEvaluationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_name": self.pipeline_name,
            "retrieval_mode": self.retrieval_mode,
            "total_queries": self.total_queries,
            "retrieval_metrics": {
                "mean_recall_at_k": round(self.mean_recall_at_k, 4),
                "mean_mrr": round(self.mean_mrr, 4),
                "mean_ndcg": round(self.mean_ndcg, 4),
            },
            "context_metrics": {
                "mean_context_precision": round(self.mean_context_precision, 4),
                "mean_context_recall": round(self.mean_context_recall, 4),
            },
            "answer_metrics": {
                "mean_faithfulness": round(self.mean_faithfulness, 4),
                "mean_answer_relevance": round(self.mean_answer_relevance, 4),
            },
            "latency_metrics": {
                "mean_latency_ms": round(self.mean_latency_ms, 1),
                "p50_latency_ms": round(self.p50_latency_ms, 1),
                "p95_latency_ms": round(self.p95_latency_ms, 1),
                "mean_retrieval_latency_ms": round(self.mean_retrieval_latency_ms, 1),
                "mean_generation_latency_ms": round(self.mean_generation_latency_ms, 1),
            },
            "efficiency_metrics": {
                "cache_hit_rate": round(self.cache_hit_rate, 4),
                "total_inferences": self.total_inferences,
                "total_tokens": self.total_tokens,
            },
            "item_results": [
                {
                    "item_id": it.item_id,
                    "query": it.query,
                    "category": it.category,
                    "recall_at_k": round(it.recall_at_k, 4),
                    "mrr": round(it.mrr, 4),
                    "ndcg": round(it.ndcg, 4),
                    "context_precision": round(it.context_precision, 4),
                    "context_recall": round(it.context_recall, 4),
                    "faithfulness": round(it.faithfulness, 4),
                    "answer_relevance": round(it.answer_relevance, 4),
                    "total_latency_ms": it.total_latency_ms,
                    "cache_hit": it.cache_hit,
                    "retrieved_pages": it.retrieved_pages,
                }
                for it in self.item_results
            ],
        }
