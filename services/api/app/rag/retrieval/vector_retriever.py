import time
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models import Document, DocumentChunk
from app.db.session import get_session_factory
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.rag.embeddings.registry import get_embedding_provider
from app.rag.retrieval.models import RetrievedChunk


class VectorRetriever:
    """
    Baseline dense vector retrieval service backed by PostgreSQL + pgvector HNSW index.
    Enforces strict multi-tenant isolation across workspace_id and project_id.
    """

    def __init__(self, embedding_provider: Optional[BaseEmbeddingProvider] = None):
        self.embedding_provider = embedding_provider or get_embedding_provider()

    async def retrieve(
        self,
        query: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        top_k: int = 5,
        document_ids: Optional[List[uuid.UUID]] = None,
        score_threshold: float = 0.0,
        session: Optional[AsyncSession] = None,
    ) -> List[RetrievedChunk]:
        """
        Executes vector similarity search against indexed document chunks.
        Strictly enforces workspace and project boundaries.
        """
        if not query or not query.strip():
            return []

        start_emb = time.time()
        # 1. Compute query vector
        query_vector = await self.embedding_provider.embed_text(query.strip())
        self.embedding_provider.validate_dimension(query_vector)
        emb_latency = time.time() - start_emb

        session_factory = get_session_factory()
        if session is not None:
            return await self._execute_search(
                session=session,
                query_vector=query_vector,
                workspace_id=workspace_id,
                project_id=project_id,
                top_k=top_k,
                document_ids=document_ids,
                score_threshold=score_threshold,
                emb_latency=emb_latency,
            )

        async with session_factory() as sess:
            return await self._execute_search(
                session=sess,
                query_vector=query_vector,
                workspace_id=workspace_id,
                project_id=project_id,
                top_k=top_k,
                document_ids=document_ids,
                score_threshold=score_threshold,
                emb_latency=emb_latency,
            )

    async def _execute_search(
        self,
        session: AsyncSession,
        query_vector: List[float],
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        top_k: int,
        document_ids: Optional[List[uuid.UUID]],
        score_threshold: float,
        emb_latency: float,
    ) -> List[RetrievedChunk]:
        start_search = time.time()

        # Cosine distance expression using pgvector
        distance_expr = DocumentChunk.embedding.cosine_distance(query_vector)
        similarity_expr = (1.0 - distance_expr).label("similarity")

        stmt = (
            select(
                DocumentChunk,
                Document.original_filename,
                similarity_expr,
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.workspace_id == workspace_id,
                DocumentChunk.project_id == project_id,
                DocumentChunk.embedding.isnot(None),
                Document.deleted_at.is_(None),
            )
        )

        if document_ids:
            stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

        # Order by ascending cosine distance (HNSW index acceleration)
        stmt = stmt.order_by(distance_expr.asc()).limit(top_k)

        res = await session.execute(stmt)
        rows = res.all()
        search_latency = time.time() - start_search

        retrieved: List[RetrievedChunk] = []
        for chunk, filename, score in rows:
            sim_score = float(score) if score is not None else 0.0
            if sim_score < score_threshold:
                continue

            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_filename=filename,
                    workspace_id=chunk.workspace_id,
                    project_id=chunk.project_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    slide_number=chunk.slide_number,
                    slide_title=chunk.slide_title,
                    section_path=chunk.section_path,
                    heading=chunk.heading,
                    similarity_score=sim_score,
                )
            )

        logger.debug(
            "Vector search: %d chunks found (embed_time=%.3fs, db_time=%.3fs, top_k=%d)",
            len(retrieved),
            emb_latency,
            search_latency,
            top_k,
        )
        return retrieved
