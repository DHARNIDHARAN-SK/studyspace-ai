from app.workers.celery_app import celery_app
from app.workers.tasks import ingest_document_task

__all__ = ["celery_app", "ingest_document_task"]
