import math
import re
from typing import List, Tuple

from app.rag.retrieval.models import RetrievedChunk


def _is_chunk_relevant(
    chunk: RetrievedChunk,
    page_start: int,
    page_end: int,
    ground_truth_keywords: List[str],
) -> Tuple[bool, float]:
    """
    Determines if a retrieved chunk is relevant to the ground truth item.
    Returns (is_relevant, relevance_weight).
    """
    chunk_page = chunk.page_start or 0
    content_lower = chunk.content.lower()

    # Exact page match
    page_matched = False
    if chunk_page > 0 and page_start > 0:
        if (page_start - 1) <= chunk_page <= (page_end + 1):
            page_matched = True

    # Keyword overlap
    matched_keywords = sum(1 for kw in ground_truth_keywords if kw.lower() in content_lower)
    keyword_ratio = matched_keywords / max(1, len(ground_truth_keywords))

    if page_matched and keyword_ratio >= 0.2:
        return True, 1.0
    elif page_matched:
        return True, 0.8
    elif keyword_ratio >= 0.4:
        return True, 0.6
    elif keyword_ratio >= 0.25:
        return True, 0.4

    return False, 0.0


def calculate_recall_at_k(
    retrieved_chunks: List[RetrievedChunk],
    page_start: int,
    page_end: int,
    ground_truth_keywords: List[str],
    k: int = 5,
) -> float:
    """
    Computes Recall@K:
    Proportion of target evidence found in the top-K retrieved chunks.
    """
    top_k_chunks = retrieved_chunks[:k]
    if not top_k_chunks:
        return 0.0

    relevant_found = any(
        _is_chunk_relevant(c, page_start, page_end, ground_truth_keywords)[0]
        for c in top_k_chunks
    )
    if not relevant_found:
        return 0.0

    # Weight by keyword coverage across all top-K chunks
    all_content = " ".join(c.content.lower() for c in top_k_chunks)
    matched_kw = sum(1 for kw in ground_truth_keywords if kw.lower() in all_content)
    coverage = matched_kw / max(1, len(ground_truth_keywords))

    return min(1.0, max(0.5, coverage))


def calculate_mrr(
    retrieved_chunks: List[RetrievedChunk],
    page_start: int,
    page_end: int,
    ground_truth_keywords: List[str],
) -> float:
    """
    Computes Mean Reciprocal Rank (MRR):
    1 / rank of the first relevant chunk retrieved (1-indexed). Returns 0.0 if not found.
    """
    for rank_idx, chunk in enumerate(retrieved_chunks):
        is_rel, _ = _is_chunk_relevant(chunk, page_start, page_end, ground_truth_keywords)
        if is_rel:
            return 1.0 / (rank_idx + 1)
    return 0.0


def calculate_ndcg(
    retrieved_chunks: List[RetrievedChunk],
    page_start: int,
    page_end: int,
    ground_truth_keywords: List[str],
    k: int = 5,
) -> float:
    """
    Computes Normalized Discounted Cumulative Gain (nDCG@K):
    Graded relevance discounted by position, normalized by Ideal DCG.
    """
    top_k_chunks = retrieved_chunks[:k]
    if not top_k_chunks:
        return 0.0

    dcg = 0.0
    relevance_scores = []
    for idx, chunk in enumerate(top_k_chunks):
        _, weight = _is_chunk_relevant(chunk, page_start, page_end, ground_truth_keywords)
        relevance_scores.append(weight)
        rank = idx + 1
        dcg += weight / math.log2(rank + 1)

    # Ideal DCG: best possible ordering of relevance weights
    ideal_scores = sorted(relevance_scores, reverse=True)
    if not any(ideal_scores):
        return 0.0

    idcg = sum(score / math.log2(idx + 2) for idx, score in enumerate(ideal_scores))
    if idcg == 0.0:
        return 0.0

    return min(1.0, dcg / idcg)


def calculate_context_precision(
    retrieved_chunks: List[RetrievedChunk],
    page_start: int,
    page_end: int,
    ground_truth_keywords: List[str],
) -> float:
    """
    Computes Context Precision:
    Fraction of retrieved chunks that are actually relevant to the ground truth item.
    """
    if not retrieved_chunks:
        return 0.0

    relevant_count = sum(
        1
        for c in retrieved_chunks
        if _is_chunk_relevant(c, page_start, page_end, ground_truth_keywords)[0]
    )
    return relevant_count / len(retrieved_chunks)


def calculate_context_recall(
    retrieved_context: str,
    ground_truth_answer: str,
    ground_truth_keywords: List[str],
) -> float:
    """
    Computes Context Recall:
    Fraction of ground-truth key facts/terms present in the compiled retrieved context.
    """
    if not retrieved_context or not ground_truth_keywords:
        return 0.0

    context_lower = retrieved_context.lower()
    matched = sum(1 for kw in ground_truth_keywords if kw.lower() in context_lower)
    return min(1.0, matched / len(ground_truth_keywords))


def calculate_faithfulness(answer: str, retrieved_context: str) -> float:
    """
    Computes Faithfulness:
    Measures the degree to which factual statements in the answer are grounded in context.
    Penalizes hallucinated assertions not found in the source excerpts.
    """
    if not answer.strip():
        return 0.0

    # Insufficient evidence rule is 100% faithful if context is empty
    if "insufficient evidence" in answer.lower():
        return 1.0

    if not retrieved_context.strip():
        return 0.0

    context_lower = retrieved_context.lower()
    sentences = [s.strip() for s in re.split(r"[.!?\n]", answer) if len(s.strip()) > 15]

    if not sentences:
        return 1.0

    supported_count = 0
    for s in sentences:
        # Extract meaningful terms (length > 3)
        words = [w.lower() for w in re.findall(r"\b[A-Za-z0-9_-]{4,}\b", s)]
        if not words:
            supported_count += 1
            continue

        matches = sum(1 for w in words if w in context_lower)
        sentence_grounding = matches / len(words)
        if sentence_grounding >= 0.5:
            supported_count += 1

    return min(1.0, supported_count / len(sentences))


def calculate_answer_relevance(
    answer: str,
    query: str,
    ground_truth_answer: str,
) -> float:
    """
    Computes Answer Relevance:
    Evaluates semantic coverage of key entities and concepts between the generated answer
    and the reference ground truth answer for the target query.
    """
    if not answer.strip():
        return 0.0

    ans_lower = answer.lower()
    gt_words = set(re.findall(r"\b[A-Za-z0-9_-]{4,}\b", ground_truth_answer.lower()))

    # Ignore common stop-words
    stopwords = {"that", "with", "this", "from", "they", "have", "were", "been", "their", "which", "about", "more", "also"}
    meaningful_gt = gt_words - stopwords

    if not meaningful_gt:
        return 1.0

    matches = sum(1 for w in meaningful_gt if w in ans_lower)
    return min(1.0, matches / len(meaningful_gt))


def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculates percentile (e.g. 50.0 for p50, 95.0 for p95)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = (percentile / 100.0) * (len(sorted_vals) - 1)
    lower = math.floor(idx)
    upper = math.ceil(idx)
    if lower == upper:
        return float(sorted_vals[int(idx)])
    weight = idx - lower
    return float(sorted_vals[lower] * (1.0 - weight) + sorted_vals[upper] * weight)
