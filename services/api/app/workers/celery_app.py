from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "studyspace_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_time_limit=600,       # 10 minutes max for large 500-page files
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,
)
