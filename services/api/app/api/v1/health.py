from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import check_db_health, check_database_configured

router = APIRouter(tags=["Health"])


class HealthStatus(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: str
    database: Optional[dict] = None


@router.get("/health", response_model=HealthStatus)
async def get_health() -> HealthStatus:
    db_info = None
    if check_database_configured():
        db_info = await check_db_health()

    return HealthStatus(
        status="healthy",
        version="0.1.0",
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=db_info,
    )


@router.get("/health/db")
async def get_db_health() -> dict:
    """Dedicated liveness/readiness probe for database and pgvector."""
    return await check_db_health()
