from datetime import datetime, timezone
import time
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import logger
from app.db.models import Document, DocumentChunk, IngestionJob
from app.db.session import get_session_factory
from app.rag.chunking.structure_aware import StructureAwareChunker
from app.rag.parsing.registry import get_parser_for_filename
from app.services.storage import DOCUMENTS_BUCKET, LocalStorageProvider, calculate_sha256


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IngestionError(AppError):
    def __init__(self, message: str, code: str = "INGESTION_FAILED", status_code: int = 500):
        super().__init__(message=message, code=code, status_code=status_code)


async def run_document_ingestion(
    document_id: uuid.UUID | str,
    workspace_id: uuid.UUID | str,
    project_id: uuid.UUID | str,
    job_id: Optional[uuid.UUID | str] = None,
    storage_provider: Optional[Any] = None,
    generate_embeddings: bool = True,
) -> Dict[str, Any]:
    """
    Executes the complete document ingestion pipeline:
      1. Verification of document and project ownership
      2. Retrieval of private storage file
      3. Format-specific parsing & structure extraction
      4. Structure-aware chunking preserving provenance
      5. Atomic database persistence of chunks and job state
    """
    doc_uuid = uuid.UUID(str(document_id))
    ws_uuid = uuid.UUID(str(workspace_id))
    proj_uuid = uuid.UUID(str(project_id))
    job_uuid = uuid.UUID(str(job_id)) if job_id else None

    session_factory = get_session_factory()
    start_time = time.time()

    logger.info(
        "Starting document ingestion for document_id=%s, project_id=%s, workspace_id=%s",
        doc_uuid,
        proj_uuid,
        ws_uuid,
    )

    # 1. Fetch document and verify authorization & ownership
    async with session_factory() as session:
        stmt = (
            select(Document)
            .where(
                Document.id == doc_uuid,
                Document.workspace_id == ws_uuid,
                Document.project_id == proj_uuid,
                Document.deleted_at.is_(None),
            )
        )
        res = await session.execute(stmt)
        document = res.scalar_one_or_none()
        if not document:
            raise IngestionError(
                f"Document {doc_uuid} not found or unauthorized for workspace {ws_uuid}.",
                code="DOCUMENT_NOT_FOUND",
                status_code=404,
            )

        # Retrieve or create ingestion job record
        if job_uuid:
            job_stmt = select(IngestionJob).where(IngestionJob.id == job_uuid)
            job_res = await session.execute(job_stmt)
            job = job_res.scalar_one_or_none()
        else:
            job_stmt = (
                select(IngestionJob)
                .where(IngestionJob.document_id == doc_uuid)
                .order_by(IngestionJob.created_at.desc())
            )
            job_res = await session.execute(job_stmt)
            job = job_res.scalars().first()

        if not job:
            job = IngestionJob(
                document_id=doc_uuid,
                document_version=document.document_version,
                job_type="full_ingestion",
                status="running",
                stage="extracting",
                started_at=utc_now(),
                attempt_count=1,
            )
            session.add(job)
        else:
            job.status = "running"
            job.stage = "extracting"
            job.started_at = utc_now()
            job.attempt_count += 1

        document.ingestion_status = "extracting"
        document.ingestion_error_code = None
        document.ingestion_error_message = None
        await session.commit()

        storage_path = document.storage_path
        filename = document.original_filename
        doc_version = document.document_version

    # 2. Retrieve file bytes from storage provider
    try:
        if storage_provider is None:
            storage_provider = LocalStorageProvider(base_dir=settings.UPLOAD_DIR)

        file_bytes = await storage_provider.get_object(
            bucket=DOCUMENTS_BUCKET,
            path=storage_path,
        )
    except Exception as exc:
        logger.error("Storage fetch failed for document %s: %s", doc_uuid, exc)
        await _record_failure(
            doc_uuid,
            job_uuid,
            error_code="STORAGE_FETCH_FAILED",
            error_message="Could not read document from private storage.",
        )
        raise IngestionError("Could not retrieve document file from storage.")

    # 3. Checksum verification
    computed_checksum = calculate_sha256(file_bytes)

    # 4. Parse document structure
    try:
        parser = get_parser_for_filename(filename)
        parsed_doc = parser.parse(file_bytes, filename)
    except AppError as app_err:
        logger.warning("Parser error for document %s: %s", doc_uuid, app_err.message)
        await _record_failure(
            doc_uuid,
            job_uuid,
            error_code=app_err.code,
            error_message=app_err.message,
        )
        raise
    except Exception as exc:
        logger.error("Unexpected parsing exception for document %s: %s", doc_uuid, exc)
        await _record_failure(
            doc_uuid,
            job_uuid,
            error_code="PARSER_EXCEPTION",
            error_message="Document parsing encountered an internal error.",
        )
        raise IngestionError(f"Parsing failed for {filename}: {str(exc)}")

    # 5. Update stage to chunking
    async with session_factory() as session:
        doc_stmt = select(Document).where(Document.id == doc_uuid)
        d_res = await session.execute(doc_stmt)
        d = d_res.scalar_one_or_none()
        if d:
            d.ingestion_status = "chunking"
        if job_uuid:
            j_stmt = select(IngestionJob).where(IngestionJob.id == job_uuid)
            j_res = await session.execute(j_stmt)
            j = j_res.scalar_one_or_none()
            if j:
                j.stage = "chunking"
        await session.commit()

    # 6. Chunk parsed document
    try:
        chunker = StructureAwareChunker(
            target_chunk_size=1000,
            chunk_overlap=150,
            min_chunk_size=50,
            max_chunk_size=1600,
        )
        raw_chunks = chunker.chunk_document(parsed_doc)
    except Exception as exc:
        logger.error("Chunking failed for document %s: %s", doc_uuid, exc)
        await _record_failure(
            doc_uuid,
            job_uuid,
            error_code="CHUNKING_FAILED",
            error_message="Document chunking failed.",
        )
        raise IngestionError(f"Chunking failed for {filename}: {str(exc)}")

    # Invariant: An indexed/searchable document MUST have chunk_count > 0
    if not raw_chunks or len(raw_chunks) == 0:
        err_msg = (
            f"Document parsing produced 0 extractable text chunks. "
            f"{'The PDF appears scanned or image-only without an OCR text layer.' if parsed_doc.is_scanned else 'The document contains no readable text content.'}"
        )
        logger.warning("Ingestion rejected document %s (%s): %s", doc_uuid, filename, err_msg)
        await _record_failure(
            doc_uuid,
            job_uuid,
            error_code="NO_EXTRACTABLE_TEXT",
            error_message=err_msg,
        )
        raise IngestionError(err_msg, code="NO_EXTRACTABLE_TEXT", status_code=422)

    # 7. Persist chunks atomically
    async with session_factory() as session:
        async with session.begin():
            # Idempotency: delete any existing chunks for this document & version
            await session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == doc_uuid,
                    DocumentChunk.document_version == doc_version,
                )
            )

            # Insert new chunks
            db_chunks = [
                DocumentChunk(
                    workspace_id=ws_uuid,
                    project_id=proj_uuid,
                    document_id=doc_uuid,
                    document_version=doc_version,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    token_count=c.token_count,
                    content_hash=c.content_hash,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    slide_number=c.slide_number,
                    slide_title=c.slide_title,
                    section_path=c.section_path,
                    heading=c.heading,
                    source_offsets=c.source_offsets,
                )
                for c in raw_chunks
            ]
            session.add_all(db_chunks)

            # Mark stage as embedding
            doc_res = await session.execute(select(Document).where(Document.id == doc_uuid))
            doc = doc_res.scalar_one()
            doc.ingestion_status = "embedding"
            if job_uuid:
                j_res = await session.execute(select(IngestionJob).where(IngestionJob.id == job_uuid))
                j = j_res.scalar_one_or_none()
                if j:
                    j.stage = "embedding"

    # 8. Generate and persist embeddings BEFORE marking as indexed
    embedded_count = 0
    if generate_embeddings:
        try:
            from app.rag.embeddings.service import ChunkEmbeddingService
            embed_service = ChunkEmbeddingService()
            embedded_count = await embed_service.embed_document_chunks(document_id=doc_uuid)
            logger.info("Embedded %d chunks for document %s", embedded_count, doc_uuid)
        except Exception as embed_err:
            logger.error("Embedding generation failed for document %s: %s", doc_uuid, embed_err)
            await _record_failure(
                doc_uuid,
                job_uuid,
                error_code="EMBEDDING_FAILED",
                error_message=f"Failed to generate vector embeddings: {str(embed_err)}",
            )
            raise IngestionError(f"Embedding generation failed: {str(embed_err)}", code="EMBEDDING_FAILED")

    # 9. Mark document as indexed only after chunking + embeddings succeed
    duration = time.time() - start_time
    async with session_factory() as session:
        async with session.begin():
            doc_res = await session.execute(select(Document).where(Document.id == doc_uuid))
            doc = doc_res.scalar_one()
            doc.ingestion_status = "indexed"
            doc.checksum = computed_checksum
            doc.page_count = parsed_doc.page_count or parsed_doc.slide_count
            doc.parser_name = parser.parser_name
            doc.parser_version = parser.parser_version
            doc.indexed_at = utc_now()
            doc.ingestion_error_code = None
            doc.ingestion_error_message = None

            # Update IngestionJob record to 'completed'
            if job_uuid:
                j_res = await session.execute(select(IngestionJob).where(IngestionJob.id == job_uuid))
                j = j_res.scalar_one_or_none()
                if j:
                    j.status = "completed"
                    j.stage = "indexed"
                    j.finished_at = utc_now()
                    j.error_code = None
                    j.error_message = None
                    j.progress_metadata = {
                        "chunk_count": len(raw_chunks),
                        "embedded_count": embedded_count,
                        "page_count": doc.page_count,
                        "parser": parser.parser_name,
                        "is_scanned": parsed_doc.is_scanned,
                        "duration_seconds": round(duration, 3),
                    }

    # 10. Invalidate project semantic cache on successful document index
    try:
        from app.rag.cache.redis_cache import RedisSemanticCache
        cache = RedisSemanticCache()
        await cache.invalidate_project_cache(workspace_id=ws_uuid, project_id=proj_uuid)
    except Exception as cache_err:
        logger.debug("Project semantic cache invalidation skipped: %s", cache_err)

    logger.info(
        "Successfully completed ingestion for document_id=%s: %d chunks created, %d embedded in %.2fs",
        doc_uuid,
        len(raw_chunks),
        embedded_count,
        duration,
    )

    return {
        "document_id": str(doc_uuid),
        "job_id": str(job_uuid) if job_uuid else None,
        "status": "indexed",
        "page_count": parsed_doc.page_count or parsed_doc.slide_count,
        "chunk_count": len(raw_chunks),
        "embedded_count": embedded_count,
        "parser_name": parser.parser_name,
        "duration_seconds": round(duration, 3),
    }


async def _record_failure(
    document_id: uuid.UUID,
    job_id: Optional[uuid.UUID],
    error_code: str,
    error_message: str,
) -> None:
    """Helper to atomically record failure states in Document and IngestionJob tables."""
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            async with session.begin():
                d_res = await session.execute(select(Document).where(Document.id == document_id))
                doc = d_res.scalar_one_or_none()
                if doc:
                    doc.ingestion_status = "failed"
                    doc.ingestion_error_code = error_code
                    doc.ingestion_error_message = error_message

                if job_id:
                    j_res = await session.execute(select(IngestionJob).where(IngestionJob.id == job_id))
                    j = j_res.scalar_one_or_none()
                    if j:
                        j.status = "failed"
                        j.stage = "failed"
                        j.finished_at = utc_now()
                        j.error_code = error_code
                        j.error_message = error_message
    except Exception as exc:
        logger.error("Failed to record failure state for document %s: %s", document_id, exc)
