import time
from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models import DocumentChunk
from app.db.session import get_session_factory
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.rag.embeddings.registry import get_embedding_provider


class ChunkEmbeddingService:
    """
    Orchestrates vector embedding generation and persistence for document chunks.
    Ensures idempotency, batch processing, dimension validation, and metadata preservation.
    """

    def __init__(self, provider: Optional[BaseEmbeddingProvider] = None):
        self.provider = provider or get_embedding_provider()

    async def embed_document_chunks(
        self,
        document_id: uuid.UUID,
        session: Optional[AsyncSession] = None,
        force_reembed: bool = False,
        batch_size: int = 32,
    ) -> int:
        """
        Embeds chunks for a specific document and updates pgvector records in PostgreSQL.
        Returns the number of chunks successfully embedded.
        """
        session_factory = get_session_factory()

        if session is not None:
            return await self._process_chunks(
                session=session,
                document_id=document_id,
                force_reembed=force_reembed,
                batch_size=batch_size,
            )

        async with session_factory() as sess:
            async with sess.begin():
                return await self._process_chunks(
                    session=sess,
                    document_id=document_id,
                    force_reembed=force_reembed,
                    batch_size=batch_size,
                )

    async def _process_chunks(
        self,
        session: AsyncSession,
        document_id: uuid.UUID,
        force_reembed: bool,
        batch_size: int,
    ) -> int:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await session.execute(stmt)
        all_chunks = list(result.scalars().all())

        if not all_chunks:
            logger.info("No chunks found for document %s to embed.", document_id)
            return 0

        # Filter chunks that need embeddings (idempotent guard)
        chunks_to_embed = [
            c for c in all_chunks if force_reembed or c.embedding is None
        ]

        if not chunks_to_embed:
            logger.info(
                "Document %s: all %d chunks already contain embeddings. Skipping.",
                document_id,
                len(all_chunks),
            )
            return 0

        logger.info(
            "Generating embeddings for %d/%d chunks for document %s (model=%s, dim=%d)",
            len(chunks_to_embed),
            len(all_chunks),
            document_id,
            self.provider.model_id,
            self.provider.dimension,
        )

        texts = [chunk.content for chunk in chunks_to_embed]
        start_time = time.time()

        # Batch embed texts
        embeddings = await self.provider.embed_batch(texts, batch_size=batch_size)

        if len(embeddings) != len(chunks_to_embed):
            raise ValueError(
                f"Generated {len(embeddings)} embeddings but had {len(chunks_to_embed)} chunks."
            )

        # Apply embeddings to chunks
        for chunk, emb in zip(chunks_to_embed, embeddings):
            self.provider.validate_dimension(emb)
            chunk.embedding = emb
            chunk.embedding_provider = self.provider.provider_name
            chunk.embedding_model_id = self.provider.model_id
            chunk.embedding_model_version = "1"

        duration = time.time() - start_time
        logger.info(
            "Successfully embedded and saved %d chunks for document %s in %.2fs (%.1f chunks/s)",
            len(chunks_to_embed),
            document_id,
            duration,
            len(chunks_to_embed) / duration if duration > 0 else 0,
        )

        return len(chunks_to_embed)
