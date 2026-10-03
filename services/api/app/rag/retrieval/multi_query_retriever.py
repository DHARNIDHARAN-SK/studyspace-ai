import asyncio
from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.rag.reranking.base import BaseReranker
from app.rag.reranking.registry import get_reranker
from app.rag.retrieval.hybrid_retriever import HybridRetriever, HybridRetrievalResult
from app.rag.retrieval.models import RetrievedChunk


@dataclass
class MultiQueryRetrievalResult:
    """Detailed outcome of multi-query parallel hybrid retrieval and deduplication."""
    chunks: List[RetrievedChunk]
    queries: List[str]
    total_candidates: int
    deduplicated_candidates: int
    per_query_counts: Dict[str, int]
    retrieval_latency_ms: int
    rerank_latency_ms: int
    total_latency_ms: int


class MultiQueryRetriever:
    """
    Coordinates parallel hybrid retrieval across multiple query variations or decomposed sub-queries.
    Deduplicates candidate chunks, merges multi-angle evidence, and applies cross-encoder reranking
    against the primary query to produce a unified, deduplicated set of relevant chunks.
    """

    def __init__(
        self,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[BaseReranker] = None,
    ):
        self.hybrid_retriever = hybrid_retriever or HybridRetriever()
        self.reranker = reranker or get_reranker()

    async def retrieve(
        self,
        queries: List[str],
        primary_query: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        dense_top_k: int = settings.RAG_DENSE_TOP_K,
        lexical_top_k: int = settings.RAG_LEXICAL_TOP_K,
        final_top_k: int = settings.RAG_RERANK_TOP_N,
        document_ids: Optional[List[uuid.UUID]] = None,
        session: Optional[AsyncSession] = None,
    ) -> MultiQueryRetrievalResult:
        start_time = time.time()

        # Sanitize queries list
        cleaned_queries = []
        for q in queries:
            c = q.strip()
            if c and c not in cleaned_queries:
                cleaned_queries.append(c)

        if not cleaned_queries:
            cleaned_queries = [primary_query.strip()]

        # 1. Execute parallel hybrid retrieval for each query
        retrieval_start = time.time()
        tasks = [
            self.hybrid_retriever.retrieve_detailed(
                query=q,
                workspace_id=workspace_id,
                project_id=project_id,
                dense_top_k=dense_top_k,
                lexical_top_k=lexical_top_k,
                final_top_k=dense_top_k + lexical_top_k,  # retrieve full pool before reranking
                document_ids=document_ids,
                session=session,
            )
            for q in cleaned_queries
        ]

        results: List[HybridRetrievalResult] = await asyncio.gather(*tasks, return_exceptions=False)
        retrieval_latency_ms = int((time.time() - retrieval_start) * 1000)

        # 2. Deduplicate candidate chunks across all queries
        total_candidates = 0
        per_query_counts = {}
        unique_chunks_map: Dict[uuid.UUID, RetrievedChunk] = {}
        chunk_provenance: Dict[uuid.UUID, List[str]] = {}

        for q, res in zip(cleaned_queries, results):
            per_query_counts[q] = len(res.chunks)
            total_candidates += len(res.chunks)
            for chunk in res.chunks:
                cid = chunk.chunk_id
                if cid not in unique_chunks_map:
                    unique_chunks_map[cid] = chunk
                    chunk_provenance[cid] = [q]
                else:
                    # Keep maximum score and record provenance
                    existing = unique_chunks_map[cid]
                    if chunk.similarity_score > existing.similarity_score:
                        unique_chunks_map[cid] = chunk
                    if q not in chunk_provenance[cid]:
                        chunk_provenance[cid].append(q)

        deduplicated_pool = list(unique_chunks_map.values())
        deduplicated_count = len(deduplicated_pool)

        # 3. Rerank deduplicated candidates against primary query
        rerank_start = time.time()
        if deduplicated_pool:
            final_chunks = await self.reranker.rerank(
                query=primary_query,
                candidates=deduplicated_pool,
                top_n=final_top_k,
            )
        else:
            final_chunks = []
        rerank_latency_ms = int((time.time() - rerank_start) * 1000)
        total_latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "MultiQueryRetriever completed: queries=%d, total_candidates=%d, deduplicated=%d, final=%d (retrieval=%dms, rerank=%dms, total=%dms)",
            len(cleaned_queries),
            total_candidates,
            deduplicated_count,
            len(final_chunks),
            retrieval_latency_ms,
            rerank_latency_ms,
            total_latency_ms,
        )

        return MultiQueryRetrievalResult(
            chunks=final_chunks,
            queries=cleaned_queries,
            total_candidates=total_candidates,
            deduplicated_candidates=deduplicated_count,
            per_query_counts=per_query_counts,
            retrieval_latency_ms=retrieval_latency_ms,
            rerank_latency_ms=rerank_latency_ms,
            total_latency_ms=total_latency_ms,
        )
