from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import secrets
import time
from typing import Any, Dict, List, Optional
import uuid

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import SecurityScopes
import redis.asyncio as aioredis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models import ApiKey, UsageEvent
from app.db.repository import store
from app.db.session import get_db_optional


# ------------------------------------------------------------------------------
# In-memory Rate Limiter Fallback (sliding 60-second window)
# ------------------------------------------------------------------------------
_in_memory_rate_limit: Dict[str, List[float]] = {}


def hash_api_key(key: str) -> str:
    """Computes SHA-256 hash of plaintext API key."""
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()


def generate_api_key_pair() -> tuple[str, str, str]:
    """
    Generates a cryptographically secure API key.
    Returns: (raw_key, key_prefix, key_hash)
    """
    token = secrets.token_hex(24)
    raw_key = f"sk_live_{token}"
    key_prefix = f"sk_live_{token[:6]}..."
    key_hash = hash_api_key(raw_key)
    return raw_key, key_prefix, key_hash


async def check_rate_limit(key_id: str, limit_rpm: int = 100) -> bool:
    """
    Checks rate limit using Redis if available, with graceful in-memory fallback.
    Returns True if permitted, False if limit exceeded.
    """
    now = time.time()
    cutoff = now - 60.0

    # In-memory tracking & test override check
    timestamps = _in_memory_rate_limit.setdefault(key_id, [])
    valid_timestamps = [t for t in timestamps if t > cutoff]
    if len(valid_timestamps) >= limit_rpm:
        _in_memory_rate_limit[key_id] = valid_timestamps
        return False

    minute_bucket = int(now // 60)
    cache_key = f"rl:apikey:{key_id}:{minute_bucket}"

    # Try Redis
    if settings.REDIS_URL:
        try:
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                current = await client.incr(cache_key)
                if current == 1:
                    await client.expire(cache_key, 65)
                if current > limit_rpm:
                    return False
            finally:
                await client.aclose()
        except Exception as e:
            logger.warning(f"Redis rate limit check failed: {e}. Falling back to in-memory.")

    valid_timestamps.append(now)
    _in_memory_rate_limit[key_id] = valid_timestamps
    return True


@dataclass
class ApiKeyContext:
    key_id: str
    workspace_id: str
    created_by_user_id: str
    name: str
    scopes: List[str]
    key_prefix: str


async def get_api_key(
    security_scopes: SecurityScopes,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Optional[AsyncSession] = Depends(get_db_optional),
) -> ApiKeyContext:
    """
    FastAPI security dependency for developer endpoints.
    Validates API key authenticity, status, scope permissions, and rate limits.
    """
    raw_key: Optional[str] = None
    if x_api_key and x_api_key.strip():
        raw_key = x_api_key.strip()
    elif authorization and authorization.strip():
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].startswith("sk_live_"):
            raw_key = parts[1]

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Provide via X-API-Key header or Authorization: Bearer sk_live_...",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not raw_key.startswith("sk_live_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key format. Must begin with 'sk_live_'.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = hash_api_key(raw_key)

    # 1. Lookup key in DB or memory store
    key_record: Optional[Dict[str, Any]] = None

    if db is not None:
        try:
            stmt = select(ApiKey).where(ApiKey.key_hash == key_hash)
            result = await db.execute(stmt)
            obj = result.scalars().first()
            if obj:
                key_record = {
                    "id": str(obj.id),
                    "workspace_id": str(obj.workspace_id),
                    "created_by_user_id": str(obj.created_by_user_id),
                    "name": obj.name,
                    "key_prefix": obj.key_prefix,
                    "scopes": obj.scopes or [],
                    "status": obj.status,
                    "rate_limit_policy": obj.rate_limit_policy or {"rpm": 100},
                    "expires_at": obj.expires_at,
                    "is_db": True,
                }
        except Exception as e:
            logger.warning(f"DB lookup for API key failed: {e}. Checking memory store.")

    if key_record is None:
        # Check memory store
        for k_id, item in store.api_keys.items():
            if item.get("key_hash") == key_hash:
                key_record = {**item, "is_db": False}
                break

    if key_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unrecognized API Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 2. Check revocation / active status
    if key_record.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"API Key is {key_record.get('status')}.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 3. Check expiration
    expires_at = key_record.get("expires_at")
    if expires_at:
        now_dt = datetime.now(timezone.utc)
        if isinstance(expires_at, datetime) and expires_at < now_dt:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key has expired.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    # 4. Check scope authorization
    assigned_scopes: List[str] = key_record.get("scopes", [])
    if "*" not in assigned_scopes:
        for required_scope in security_scopes.scopes:
            if required_scope not in assigned_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required scope: '{required_scope}'.",
                )

    # 5. Check Rate Limiter
    rpm = key_record.get("rate_limit_policy", {}).get("rpm", 100)
    allowed = await check_rate_limit(key_record["id"], limit_rpm=rpm)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({rpm} req/min). Please back off.",
            headers={"Retry-After": "60"},
        )

    # 6. Update last_used_at
    now_utc = datetime.now(timezone.utc)
    if key_record.get("is_db") and db is not None:
        try:
            await db.execute(
                update(ApiKey)
                .where(ApiKey.id == uuid.UUID(key_record["id"]))
                .values(last_used_at=now_utc)
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not update last_used_at on API key: {e}")
    elif key_record["id"] in store.api_keys:
        store.api_keys[key_record["id"]]["last_used_at"] = now_utc

    return ApiKeyContext(
        key_id=key_record["id"],
        workspace_id=key_record["workspace_id"],
        created_by_user_id=key_record["created_by_user_id"],
        name=key_record["name"],
        scopes=assigned_scopes,
        key_prefix=key_record["key_prefix"],
    )
