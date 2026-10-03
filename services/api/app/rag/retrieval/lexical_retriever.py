import re
import time
from typing import List, Optional
import uuid
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models import Document, DocumentChunk
from app.db.session import get_session_factory
from app.rag.retrieval.models import RetrievedChunk


class LexicalRetriever:
    """
    Lexical / Full-Text Search (BM25 equivalent) retriever backed by PostgreSQL tsvector.
    Queries the GIN-indexed search_vector on document_chunks table with weighted relevance
    (headings weighted 'A', content weighted 'B') and length-normalized ranking.
    Strictly enforces workspace_id and project_id multi-tenant isolation.
    """

    def _sanitize_terms(self, query: str) -> List[str]:
        """Extract alphanumeric terms suitable for tsquery formatting."""
        # Find all word tokens
        tokens = re.findall(r"\b[a-zA-Z0-9_\-']+\b", query)
        sanitized = []
        for t in tokens:
            cleaned = re.sub(r"[^a-zA-Z0-9]", "", t).strip()
            if len(cleaned) >= 2:
                sanitized.append(cleaned)
        return sanitized

    async def retrieve(
        self,
        query: str,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        top_k: int = 20,
        document_ids: Optional[List[uuid.UUID]] = None,
        score_threshold: float = 0.0,
        session: Optional[AsyncSession] = None,
    ) -> List[RetrievedChunk]:
        """
        Executes PostgreSQL full-text search against indexed document chunks.
        Strictly enforces workspace and project boundaries.
        """
        if not query or not query.strip():
            return []

        clean_query = query.strip()
        terms = self._sanitize_terms(clean_query)
        if not terms:
            return []

        session_factory = get_session_factory()
        if session is not None:
            return await self._execute_search(
                session=session,
                clean_query=clean_query,
                terms=terms,
                workspace_id=workspace_id,
                project_id=project_id,
                top_k=top_k,
                document_ids=document_ids,
                score_threshold=score_threshold,
            )

        async with session_factory() as sess:
            return await self._execute_search(
                session=sess,
                clean_query=clean_query,
                terms=terms,
                workspace_id=workspace_id,
                project_id=project_id,
                top_k=top_k,
                document_ids=document_ids,
                score_threshold=score_threshold,
            )

    async def _execute_search(
        self,
        session: AsyncSession,
        clean_query: str,
        terms: List[str],
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        top_k: int,
        document_ids: Optional[List[uuid.UUID]],
        score_threshold: float,
    ) -> List[RetrievedChunk]:
        start_search = time.time()

        # Build disjunctive query string for BM25-like term coverage
        or_query_str = " | ".join(terms)

        # tsquery expressions:
        # 1. websearch_tsquery: preserves natural phrasing and AND relationships
        # 2. or_tsquery: covers any matching term with ts_rank_cd scoring
        websearch_tsquery = func.websearch_to_tsquery("english", clean_query)
        or_tsquery = func.to_tsquery("english", or_query_str)

        # Combined tsquery: match either websearch phrase or any token
        # Combined scoring: ts_rank_cd with normalization flag 32 (scales 0..1 with length normalization)
        # We give higher weight to exact websearch matches
        rank_websearch = func.ts_rank_cd(DocumentChunk.search_vector, websearch_tsquery, 32)
        rank_or = func.ts_rank_cd(DocumentChunk.search_vector, or_tsquery, 32)
        combined_score = (func.coalesce(rank_websearch, 0.0) * 1.5 + rank_or).label("lexical_score")

        stmt = (
            select(
                DocumentChunk,
                Document.original_filename,
                combined_score,
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.workspace_id == workspace_id,
                DocumentChunk.project_id == project_id,
                DocumentChunk.search_vector.isnot(None),
                Document.deleted_at.is_(None),
                or_(
                    DocumentChunk.search_vector.op("@@")(or_tsquery),
                    DocumentChunk.search_vector.op("@@")(websearch_tsquery),
                ),
            )
        )

        if document_ids:
            stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

        # Order by highest lexical rank score
        stmt = stmt.order_by(combined_score.desc()).limit(top_k)

        res = await session.execute(stmt)
        rows = res.all()
        search_latency = time.time() - start_search

        retrieved: List[RetrievedChunk] = []
        for rank, (chunk, filename, score) in enumerate(rows, start=1):
            lex_score = float(score) if score is not None else 0.0
            if lex_score < score_threshold:
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
                    similarity_score=lex_score,
                    lexical_score=lex_score,
                    lexical_rank=rank,
                    retrieval_method="lexical",
                )
            )

        logger.debug(
            "Lexical search: %d chunks found (db_time=%.3fs, top_k=%d, query='%s')",
            len(retrieved),
            search_latency,
            top_k,
            clean_query[:50],
        )
        return retrieved
