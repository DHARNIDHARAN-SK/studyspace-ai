import asyncio
import uuid
from typing import Any, Dict, Optional
from celery.exceptions import MaxRetriesExceededError

from app.core.errors import AppError
from app.core.logging import logger
from app.rag.ingestion.pipeline import run_document_ingestion
from app.workers.celery_app import celery_app


@celery_app.task(
    name="tasks.ingest_document",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def ingest_document_task(
    self,
    document_id: str,
    workspace_id: str,
    project_id: str,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Celery background worker task for processing uploaded documents asynchronously.
    Enforces tenant boundaries by workspace_id and project_id.
    """
    logger.info(
        "Celery task started: ingest_document_task for doc=%s, project=%s, workspace=%s, attempt=%d",
        document_id,
        project_id,
        workspace_id,
        self.request.retries + 1,
    )

    try:
        # Run async pipeline inside event loop
        result = asyncio.run(
            run_document_ingestion(
                document_id=uuid.UUID(document_id),
                workspace_id=uuid.UUID(workspace_id),
                project_id=uuid.UUID(project_id),
                job_id=uuid.UUID(job_id) if job_id else None,
                generate_embeddings=True,
            )
        )
        logger.info("Celery task completed successfully: doc=%s", document_id)
        return result
    except AppError as app_err:
        # Permanent domain validation / format failure: DO NOT retry
        logger.warning(
            "Permanent failure in ingest_document_task (no retry): doc=%s, code=%s, msg=%s",
            document_id,
            app_err.code,
            app_err.message,
        )
        return {
            "status": "failed",
            "document_id": document_id,
            "error_code": app_err.code,
            "error_message": app_err.message,
        }
    except Exception as exc:
        # Transient infrastructure or connection failure: retry if attempts remain
        logger.error(
            "Transient failure in ingest_document_task: doc=%s, exc=%s",
            document_id,
            exc,
            exc_info=True,
        )
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for document %s", document_id)
            return {
                "status": "failed",
                "document_id": document_id,
                "error_code": "MAX_RETRIES_EXCEEDED",
                "error_message": "Document processing exceeded maximum retry attempts.",
            }
