from typing import Dict, List, Optional
import uuid

from app.core.config import settings
from app.core.logging import logger
from app.rag.retrieval.models import RetrievedChunk


class ReciprocalRankFusion:
    """
    Combines ranked candidate lists from disparate retrieval strategies (e.g. dense vector and
    lexical full-text search) using Reciprocal Rank Fusion (RRF).

    Formula:
        RRF_Score(d) = sum_{m in M} ( w_m / (k + rank_m(d)) )

    Where:
        - k is a rank-smoothing constant (default 60).
        - rank_m(d) is the 1-based position of document d in ranking list m.
        - w_m is an optional weighting multiplier for retrieval path m (default 1.0).
    """

    def __init__(
        self,
        k: int = settings.RAG_RRF_K,
        dense_weight: float = 1.0,
        lexical_weight: float = 1.0,
    ):
        self.k = k if k > 0 else 60
        self.dense_weight = dense_weight
        self.lexical_weight = lexical_weight

    def fuse(
        self,
        dense_candidates: List[RetrievedChunk],
        lexical_candidates: List[RetrievedChunk],
        top_n: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        """
        Merges dense and lexical candidate lists into a unified ranked list.
        Tracks origin provenance (dense_rank, dense_score, lexical_rank, lexical_score, retrieval_method).
        """
        # Map chunk_id to candidate object and metadata
        fused_map: Dict[uuid.UUID, RetrievedChunk] = {}
        rrf_scores: Dict[uuid.UUID, float] = {}

        # 1. Process Dense Candidates
        for rank, chunk in enumerate(dense_candidates, start=1):
            cid = chunk.chunk_id
            chunk.dense_rank = rank
            chunk.dense_score = chunk.similarity_score
            chunk.retrieval_method = "dense"

            score = self.dense_weight / (self.k + rank)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + score
            fused_map[cid] = chunk

        # 2. Process Lexical Candidates
        for rank, chunk in enumerate(lexical_candidates, start=1):
            cid = chunk.chunk_id
            score = self.lexical_weight / (self.k + rank)

            if cid in fused_map:
                # Candidate present in both retrieval streams -> Hybrid
                existing = fused_map[cid]
                existing.lexical_rank = rank
                existing.lexical_score = chunk.lexical_score or chunk.similarity_score
                existing.retrieval_method = "hybrid"
                rrf_scores[cid] = rrf_scores.get(cid, 0.0) + score
            else:
                chunk.lexical_rank = rank
                chunk.lexical_score = chunk.lexical_score or chunk.similarity_score
                chunk.retrieval_method = "lexical"
                rrf_scores[cid] = score
                fused_map[cid] = chunk

        # 3. Assign final RRF score and sort
        fused_list: List[RetrievedChunk] = []
        for cid, chunk in fused_map.items():
            final_rrf = rrf_scores[cid]
            chunk.rrf_score = final_rrf
            chunk.similarity_score = final_rrf  # RRF score becomes effective relevance score
            fused_list.append(chunk)

        # Sort descending by RRF score
        fused_list.sort(key=lambda c: c.rrf_score or 0.0, reverse=True)

        if top_n is not None and top_n > 0:
            fused_list = fused_list[:top_n]

        logger.debug(
            "RRF Fusion: dense=%d, lexical=%d -> fused=%d (k=%d, top_n=%s)",
            len(dense_candidates),
            len(lexical_candidates),
            len(fused_list),
            self.k,
            top_n,
        )

        return fused_list
