from abc import ABC, abstractmethod
from typing import List

from app.rag.retrieval.models import RetrievedChunk


class BaseReranker(ABC):
    """
    Abstract interface for Phase 7 candidate rerankers.
    Re-scores and re-ranks retrieved chunks based on deeper query-passage cross-attention
    or cross-feature relevance.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_n: int = 5,
    ) -> List[RetrievedChunk]:
        """
        Reranks candidate chunks and returns the top_n most relevant chunks.
        Must populate `rerank_score` on each returned chunk.
        """
        pass
