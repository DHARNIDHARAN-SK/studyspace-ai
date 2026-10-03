import time
from typing import AsyncGenerator, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import logger


def get_async_database_url(url: Optional[str] = None) -> Optional[str]:
    """
    Normalizes a PostgreSQL connection URL to the asyncpg dialect for SQLAlchemy async engine.
    Example: postgresql://... -> postgresql+asyncpg://...
    """
    db_url = url or settings.DATABASE_URL
    if not db_url:
        return None

    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return db_url


def check_database_configured() -> bool:
    """Checks whether the database connection string is present."""
    has_db = bool(settings.DATABASE_URL)
    if not has_db:
        logger.debug("Database URL is not configured. Running in stateless or development mock mode.")
    return has_db


# Global async engine and sessionmaker instances
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> Optional[AsyncEngine]:
    """Lazily initializes and returns the SQLAlchemy AsyncEngine instance."""
    global _engine
    if _engine is None:
        async_url = get_async_database_url()
        if async_url:
            import os
            from sqlalchemy.pool import NullPool

            is_test = bool(os.environ.get("PYTEST_CURRENT_TEST") or settings.APP_ENV in ("test", "testing"))
            if is_test:
                _engine = create_async_engine(
                    async_url,
                    poolclass=NullPool,
                    echo=settings.DEBUG,
                )
            else:
                _engine = create_async_engine(
                    async_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    echo=settings.DEBUG,
                )
            logger.info("Initialized SQLAlchemy async engine for PostgreSQL.")
    return _engine


def get_session_factory() -> Optional[async_sessionmaker[AsyncSession]]:
    """Lazily initializes and returns the async_sessionmaker factory."""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        if engine is not None:
            _async_session_maker = async_sessionmaker(
                bind=engine,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
                class_=AsyncSession,
            )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session per request.
    Transactions are rolled back automatically if an unhandled exception occurs.
    """
    session_factory = get_session_factory()
    if session_factory is None:
        raise RuntimeError("Database connection is not configured or engine failed to initialize.")

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_health() -> dict:
    """
    Verifies live PostgreSQL database connectivity, pgvector extension,
    and public table schema count.
    """
    engine = get_engine()
    if engine is None:
        return {
            "status": "unconfigured",
            "message": "DATABASE_URL is not set",
            "pgvector_available": False,
            "latency_ms": None,
        }

    start_time = time.perf_counter()
    try:
        async with engine.connect() as conn:
            # 1. Connectivity test
            await conn.execute(text("SELECT 1"))

            # 2. Check pgvector extension
            res_ext = await conn.execute(
                text("SELECT default_version, installed_version FROM pg_available_extensions WHERE name = 'vector'")
            )
            ext_row = res_ext.fetchone()
            pgvector_installed = bool(ext_row and ext_row[1] is not None)
            pgvector_version = ext_row[1] if (ext_row and ext_row[1]) else None

            # 3. Check public schema table count
            res_tables = await conn.execute(
                text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
            )
            table_count = res_tables.scalar() or 0

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return {
                "status": "healthy",
                "pgvector_installed": pgvector_installed,
                "pgvector_version": pgvector_version,
                "table_count": table_count,
                "latency_ms": latency_ms,
            }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning(f"Database health check failed: {e}")
        return {
            "status": "unreachable",
            "error": str(e),
            "pgvector_installed": False,
            "latency_ms": latency_ms,
        }
