import asyncio
from dataclasses import dataclass, field
import time
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.rag.fusion.rrf import ReciprocalRankFusion
from app.rag.reranking.base import BaseReranker
from app.rag.reranking.registry import get_reranker
from app.rag.retrieval.lexical_retriever import LexicalRetriever
from app.rag.retrieval.models import RetrievedChunk
from app.rag.retrieval.vector_retriever import VectorRetriever


@dataclass
class HybridRetrievalResult:
    """Detailed result of hybrid retrieval with provenance and latency breakdown."""
    chunks: List[RetrievedChunk]
    dense_candidates: List[RetrievedChunk]
    lexical_candidates: List[RetrievedChunk]
    fused_candidates: List[RetrievedChunk]
    dense_latency_ms: int
    lexical_latency_ms: int
    fusion_latency_ms: int
    rerank_latency_ms: int
    total_latency_ms: int


class HybridRetriever:
    """
    Phase 7 Advanced Hybrid Retriever.
    Executes parallel Dense Vector Search + Lexical FTS (BM25 equivalent) ->
    Candidate Fusion via Reciprocal Rank Fusion (RRF) ->
    Context Reranking -> Top Relevant Chunks.
    Strictly tenant-scoped by workspace_id and project_id.
    """

    def __init__(
        self,
        vector_retriever: Optional[VectorRetriever] = None,
        lexical_retriever: Optional[LexicalRetriever] = None,
        fusion: Optional[ReciprocalRankFusion] = None,
        reranker: Optional[BaseReranker] = None,
    ):
        self.vector_retriever = vector_retriever or VectorRetriever()
        self.lexical_retriever = lexical_retriever or LexicalRetriever()
        self.fusion = fusion or ReciprocalRankFusion(k=settings.RAG_RRF_K)
        self.reranker = reranker or get_reranker()

    async def retrieve(
        self,
        query: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        dense_top_k: int = settings.RAG_DENSE_TOP_K,
        lexical_top_k: int = settings.RAG_LEXICAL_TOP_K,
        final_top_k: int = settings.RAG_RERANK_TOP_N,
        document_ids: Optional[List[uuid.UUID]] = None,
        session: Optional[AsyncSession] = None,
    ) -> List[RetrievedChunk]:
        """Convenience method returning top-N reranked chunks directly."""
        result = await self.retrieve_detailed(
            query=query,
            workspace_id=workspace_id,
            project_id=project_id,
            dense_top_k=dense_top_k,
            lexical_top_k=lexical_top_k,
            final_top_k=final_top_k,
            document_ids=document_ids,
            session=session,
        )
        return result.chunks

    async def retrieve_detailed(
        self,
        query: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        dense_top_k: int = settings.RAG_DENSE_TOP_K,
        lexical_top_k: int = settings.RAG_LEXICAL_TOP_K,
        final_top_k: int = settings.RAG_RERANK_TOP_N,
        document_ids: Optional[List[uuid.UUID]] = None,
        session: Optional[AsyncSession] = None,
    ) -> HybridRetrievalResult:
        """
        Executes parallel hybrid search with full intermediate candidate tracking and latency benchmarking.
        """
        total_start = time.time()

        # 1. Concurrently run Dense Vector Search & Lexical Search
        dense_start = time.time()
        lex_start = time.time()

        dense_task = self.vector_retriever.retrieve(
            query=query,
            workspace_id=workspace_id,
            project_id=project_id,
            top_k=dense_top_k,
            document_ids=document_ids,
            session=session,
        )
        lexical_task = self.lexical_retriever.retrieve(
            query=query,
            workspace_id=workspace_id,
            project_id=project_id,
            top_k=lexical_top_k,
            document_ids=document_ids,
            session=session,
        )

        dense_candidates, lexical_candidates = await asyncio.gather(dense_task, lexical_task)
        dense_latency_ms = int((time.time() - dense_start) * 1000)
        lexical_latency_ms = int((time.time() - lex_start) * 1000)

        # 2. Reciprocal Rank Fusion
        fusion_start = time.time()
        fused_candidates = self.fusion.fuse(
            dense_candidates=dense_candidates,
            lexical_candidates=lexical_candidates,
        )
        fusion_latency_ms = int((time.time() - fusion_start) * 1000)

        # 3. Reranking
        rerank_start = time.time()
        final_chunks = await self.reranker.rerank(
            query=query,
            candidates=fused_candidates,
            top_n=final_top_k,
        )
        rerank_latency_ms = int((time.time() - rerank_start) * 1000)
        total_latency_ms = int((time.time() - total_start) * 1000)

        logger.info(
            "Hybrid Retrieval: query='%s' -> dense=%d (%dms), lexical=%d (%dms), fused=%d (%dms), final=%d (rerank=%dms, total=%dms)",
            query[:40],
            len(dense_candidates),
            dense_latency_ms,
            len(lexical_candidates),
            lexical_latency_ms,
            len(fused_candidates),
            fusion_latency_ms,
            len(final_chunks),
            rerank_latency_ms,
            total_latency_ms,
        )

        return HybridRetrievalResult(
            chunks=final_chunks,
            dense_candidates=dense_candidates,
            lexical_candidates=lexical_candidates,
            fused_candidates=fused_candidates,
            dense_latency_ms=dense_latency_ms,
            lexical_latency_ms=lexical_latency_ms,
            fusion_latency_ms=fusion_latency_ms,
            rerank_latency_ms=rerank_latency_ms,
            total_latency_ms=total_latency_ms,
        )
