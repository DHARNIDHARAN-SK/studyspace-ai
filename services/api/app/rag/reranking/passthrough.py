from typing import List

from app.rag.reranking.base import BaseReranker
from app.rag.retrieval.models import RetrievedChunk


class PassthroughReranker(BaseReranker):
    """
    Reranker implementation that preserves original fusion/retrieval ordering and scores.
    Used when reranking is disabled or bypassed.
    """

    async def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_n: int = 5,
    ) -> List[RetrievedChunk]:
        for c in candidates:
            c.rerank_score = c.similarity_score
        return candidates[:top_n]
