from typing import Optional
from app.core.config import settings
from app.core.logging import logger


def get_database_url() -> Optional[str]:
    """Returns configured PostgreSQL database URL or None if not configured."""
    return settings.DATABASE_URL


def check_database_configured() -> bool:
    """Checks whether the database connection string is present."""
    has_db = bool(settings.DATABASE_URL)
    if not has_db:
        logger.debug("Database URL is not configured. Running in stateless or development mock mode.")
    return has_db
