import uuid
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import logger
from app.db.documents import ensure_tenant_hierarchy, get_project_document, list_project_documents
from app.db.models import Document, IngestionJob
from app.db.session import get_db
from app.rag.ingestion.pipeline import run_document_ingestion
from app.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    IngestionJobResponse,
)
from app.services.storage import (
    DOCUMENTS_BUCKET,
    LocalStorageProvider,
    build_document_storage_path,
    calculate_sha256,
    validate_file_spec,
)

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["Documents"])


def get_storage_provider() -> LocalStorageProvider:
    return LocalStorageProvider(base_dir=settings.UPLOAD_DIR)


def _to_document_response(doc: Document, chunk_count: Optional[int] = None) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        workspace_id=str(doc.workspace_id),
        project_id=str(doc.project_id),
        original_filename=doc.original_filename,
        storage_path=doc.storage_path,
        mime_type=doc.mime_type,
        extension=doc.extension,
        byte_size=doc.byte_size,
        page_count=doc.page_count,
        checksum=doc.checksum,
        document_version=doc.document_version,
        ingestion_status=doc.ingestion_status,
        ingestion_error_code=doc.ingestion_error_code,
        ingestion_error_message=doc.ingestion_error_message,
        parser_name=doc.parser_name,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        indexed_at=doc.indexed_at,
        chunk_count=chunk_count,
    )


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Asynchronously uploads and enqueues a course document for parsing and chunking.
    Enforces the 500-page requirement by returning immediately with a queued job ID.
    """
    user_uuid = uuid.UUID(current_user.id)
    ws_uuid = uuid.UUID(current_user.workspace_id)
    try:
        proj_uuid = uuid.UUID(project_id)
    except ValueError:
        raise AppError("Invalid project ID format.", code="INVALID_PROJECT_ID", status_code=400)

    # 1. Authorize workspace and project ownership
    await ensure_tenant_hierarchy(db, user_uuid, ws_uuid, proj_uuid)

    # 2. Read and validate file content
    file_bytes = await file.read()
    file_size = len(file_bytes)

    safe_name, validated_mime = validate_file_spec(
        filename=file.filename or "uploaded_document",
        file_size_bytes=file_size,
        content_type=file.content_type,
    )
    ext = f".{safe_name.split('.')[-1].lower()}"
    checksum = calculate_sha256(file_bytes)

    # 3. Check for existing duplicate document in this project (Idempotency)
    dup_stmt = select(Document).where(
        Document.project_id == proj_uuid,
        Document.checksum == checksum,
        Document.deleted_at.is_(None),
    )
    dup_res = await db.execute(dup_stmt)
    existing_doc = dup_res.scalars().first()

    if existing_doc and existing_doc.ingestion_status == "indexed":
        logger.info(
            "Idempotent upload detected: identical checksum '%s' already indexed for doc %s",
            checksum,
            existing_doc.id,
        )
        return DocumentUploadResponse(
            document=_to_document_response(existing_doc),
            job_id=str(uuid.uuid4()),
            status=existing_doc.ingestion_status,
            message="Document already exists with identical content and is fully indexed.",
        )

    # 4. Generate canonical storage path & store file
    doc_uuid = uuid.uuid4()
    storage_path = build_document_storage_path(ws_uuid, proj_uuid, doc_uuid, safe_name)
    storage_provider = get_storage_provider()

    await storage_provider.put_object(
        bucket=DOCUMENTS_BUCKET,
        path=storage_path,
        data=file_bytes,
        content_type=validated_mime,
    )

    # 5. Insert Document and IngestionJob records
    document = Document(
        id=doc_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        uploaded_by_user_id=user_uuid,
        original_filename=safe_name,
        storage_path=storage_path,
        mime_type=validated_mime,
        extension=ext,
        byte_size=file_size,
        checksum=checksum,
        document_version=1,
        ingestion_status="queued",
    )
    db.add(document)

    job_uuid = uuid.uuid4()
    job = IngestionJob(
        id=job_uuid,
        document_id=doc_uuid,
        document_version=1,
        job_type="full_ingestion",
        status="queued",
        stage="queued",
        attempt_count=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(document)

    # 6. Dispatch asynchronous ingestion job via Celery (with background_tasks fallback)
    dispatched_celery = False
    try:
        from app.workers.tasks import ingest_document_task
        ingest_document_task.delay(
            str(doc_uuid),
            str(ws_uuid),
            str(proj_uuid),
            str(job_uuid),
        )
        dispatched_celery = True
        logger.info("Successfully enqueued ingestion task to Celery for doc %s", doc_uuid)
    except Exception as celery_err:
        logger.warning(
            "Could not dispatch to Celery broker (%s); running via local background tasks.",
            celery_err,
        )

    if not dispatched_celery:
        background_tasks.add_task(
            run_document_ingestion,
            document_id=doc_uuid,
            workspace_id=ws_uuid,
            project_id=proj_uuid,
            job_id=job_uuid,
        )

    return DocumentUploadResponse(
        document=_to_document_response(document),
        job_id=str(job_uuid),
        status="queued",
        message="Document uploaded successfully and queued for background ingestion.",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """Lists all active documents for the authorized project."""
    ws_uuid = uuid.UUID(current_user.workspace_id)
    user_uuid = uuid.UUID(current_user.id)
    try:
        proj_uuid = uuid.UUID(project_id)
    except ValueError:
        raise AppError("Invalid project ID format.", code="INVALID_PROJECT_ID", status_code=400)

    await ensure_tenant_hierarchy(db, user_uuid, ws_uuid, proj_uuid)
    rows = await list_project_documents(db, ws_uuid, proj_uuid)

    docs = [_to_document_response(doc, chunk_count) for doc, chunk_count in rows]
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    project_id: str,
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Retrieves metadata and ingestion status for a specific document."""
    ws_uuid = uuid.UUID(current_user.workspace_id)
    try:
        proj_uuid = uuid.UUID(project_id)
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise AppError("Invalid ID format.", code="INVALID_ID_FORMAT", status_code=400)

    doc = await get_project_document(db, ws_uuid, proj_uuid, doc_uuid)
    return _to_document_response(doc)


@router.post("/{document_id}/retry", response_model=DocumentResponse)
async def retry_document_ingestion(
    project_id: str,
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Retries ingestion for a document that previously failed."""
    ws_uuid = uuid.UUID(current_user.workspace_id)
    try:
        proj_uuid = uuid.UUID(project_id)
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise AppError("Invalid ID format.", code="INVALID_ID_FORMAT", status_code=400)

    doc = await get_project_document(db, ws_uuid, proj_uuid, doc_uuid)

    # Reset document status
    doc.ingestion_status = "queued"
    doc.ingestion_error_code = None
    doc.ingestion_error_message = None

    job_uuid = uuid.uuid4()
    job = IngestionJob(
        id=job_uuid,
        document_id=doc_uuid,
        document_version=doc.document_version,
        job_type="full_ingestion",
        status="queued",
        stage="queued",
        attempt_count=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(doc)

    dispatched = False
    try:
        from app.workers.tasks import ingest_document_task
        ingest_document_task.delay(str(doc_uuid), str(ws_uuid), str(proj_uuid), str(job_uuid))
        dispatched = True
    except Exception:
        pass

    if not dispatched:
        background_tasks.add_task(
            run_document_ingestion,
            document_id=doc_uuid,
            workspace_id=ws_uuid,
            project_id=proj_uuid,
            job_id=job_uuid,
        )

    return _to_document_response(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    project_id: str,
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-deletes a document and its storage payload."""
    ws_uuid = uuid.UUID(current_user.workspace_id)
    try:
        proj_uuid = uuid.UUID(project_id)
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise AppError("Invalid ID format.", code="INVALID_ID_FORMAT", status_code=400)

    doc = await get_project_document(db, ws_uuid, proj_uuid, doc_uuid)

    from datetime import datetime, timezone
    doc.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    # Clean up storage payload asynchronously
    try:
        storage_provider = get_storage_provider()
        await storage_provider.delete_object(DOCUMENTS_BUCKET, doc.storage_path)
    except Exception as exc:
        logger.warning("Could not delete physical storage object: %s", exc)

    return None
