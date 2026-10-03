from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthStatus(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: str


@router.get("/health", response_model=HealthStatus)
async def get_health() -> HealthStatus:
    from app.core.config import settings

    return HealthStatus(
        status="healthy",
        version="0.1.0",
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
