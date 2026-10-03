from dataclasses import dataclass, field
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional
import uuid

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import logger
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.rag.embeddings.registry import get_embedding_provider


@dataclass
class SemanticCacheHit:
    cache_hit: bool
    similarity_score: float
    cached_query: str
    answer: str
    citations: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    dot_product = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot_product += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot_product / (math.sqrt(norm_a) * math.sqrt(norm_b))


class RedisSemanticCache:
    """
    Redis-backed semantic cache and request deduplicator for StudySpace AI.
    Guarantees strict tenant isolation across workspaces and projects.
    Fails open/gracefully if Redis is offline or encounters errors.
    """

    def __init__(
        self,
        redis_url: str = settings.REDIS_URL,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        similarity_threshold: float = settings.RAG_SEMANTIC_CACHE_SIMILARITY_THRESHOLD,
        ttl_seconds: int = settings.RAG_SEMANTIC_CACHE_TTL_SECONDS,
        lock_ttl_seconds: int = settings.RAG_REQUEST_DEDUPLICATION_TTL_SECONDS,
    ):
        self.redis_url = redis_url
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.lock_ttl_seconds = lock_ttl_seconds
        self._client: Optional[aioredis.Redis] = None

    async def get_client(self) -> Optional[aioredis.Redis]:
        """Lazy initialization of async Redis client."""
        if self._client is None:
            try:
                self._client = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0,
                )
            except Exception as e:
                logger.warning("Failed to initialize Redis client: %s", e)
                return None
        return self._client

    def _prefix(self, workspace_id: uuid.UUID, project_id: uuid.UUID) -> str:
        """Tenant-isolated Redis key prefix."""
        env_name = getattr(settings, "APP_ENV", "development")
        return f"studyspace:{env_name}:ws:{workspace_id}:proj:{project_id}"

    def _query_hash(self, query: str) -> str:
        return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()

    async def acquire_dedup_lock(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        query: str,
    ) -> Optional[str]:
        """
        Attempts to acquire a deduplication lock for an in-flight query.
        Returns a lock token if acquired, or None if another identical request is already running.
        """
        try:
            client = await self.get_client()
            if not client:
                return None
            prefix = self._prefix(workspace_id, project_id)
            lock_key = f"{prefix}:lock:req:{self._query_hash(query)}"
            token = str(uuid.uuid4())
            # SET NX EX
            acquired = await client.set(lock_key, token, ex=self.lock_ttl_seconds, nx=True)
            if acquired:
                return token
            return None
        except Exception as e:
            logger.warning("Redis acquire_dedup_lock error: %s", e)
            return None

    async def release_dedup_lock(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        query: str,
        token: str,
    ) -> None:
        """Releases the deduplication lock if the token matches."""
        try:
            client = await self.get_client()
            if not client or not token:
                return
            prefix = self._prefix(workspace_id, project_id)
            lock_key = f"{prefix}:lock:req:{self._query_hash(query)}"
            current = await client.get(lock_key)
            if current == token:
                await client.delete(lock_key)
        except Exception as e:
            logger.warning("Redis release_dedup_lock error: %s", e)

    async def lookup(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        query: str,
        query_embedding: Optional[List[float]] = None,
    ) -> Optional[SemanticCacheHit]:
        """
        Looks up semantic cache for a query embedding within the project namespace.
        If cosine similarity >= threshold, returns the cached result.
        """
        if not settings.RAG_SEMANTIC_CACHE_ENABLED:
            return None

        try:
            client = await self.get_client()
            if not client:
                return None

            prefix = self._prefix(workspace_id, project_id)
            active_set_key = f"{prefix}:semcache:active_keys"

            # 1. Fetch active entry IDs
            entry_ids = await client.smembers(active_set_key)
            if not entry_ids:
                return None

            # 2. Compute query embedding if not provided
            if query_embedding is None:
                query_embedding = await self.embedding_provider.embed_text(query)

            # 3. Retrieve all active cached entries
            keys_to_fetch = [f"{prefix}:semcache:entry:{eid}" for eid in entry_ids]
            raw_entries = await client.mget(keys_to_fetch)

            best_similarity = -1.0
            best_entry: Optional[Dict[str, Any]] = None
            expired_ids = []

            for eid, raw_json in zip(entry_ids, raw_entries):
                if not raw_json:
                    expired_ids.append(eid)
                    continue

                try:
                    entry_dict = json.loads(raw_json)
                    cached_vec = entry_dict.get("embedding")
                    if not cached_vec:
                        continue
                    sim = compute_cosine_similarity(query_embedding, cached_vec)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_entry = entry_dict
                except Exception as parse_err:
                    logger.warning("Failed to parse cached entry %s: %s", eid, parse_err)
                    expired_ids.append(eid)

            # Cleanup expired entry references
            if expired_ids:
                await client.srem(active_set_key, *expired_ids)

            if best_entry and best_similarity >= self.similarity_threshold:
                logger.info(
                    "Semantic Cache HIT (similarity=%.4f >= %.2f) for query: '%s' (matched: '%s')",
                    best_similarity,
                    self.similarity_threshold,
                    query,
                    best_entry.get("query"),
                )
                return SemanticCacheHit(
                    cache_hit=True,
                    similarity_score=best_similarity,
                    cached_query=best_entry.get("query", ""),
                    answer=best_entry.get("answer", ""),
                    citations=best_entry.get("citations", []),
                    retrieved_chunks=best_entry.get("retrieved_chunks", []),
                    metadata=best_entry.get("metadata", {}),
                )

            return None
        except Exception as e:
            logger.warning("Redis semantic cache lookup error: %s", e)
            return None

    async def store(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        query: str,
        answer: str,
        citations: List[Dict[str, Any]],
        retrieved_chunks: List[Dict[str, Any]],
        query_embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Stores query, embedding, and generated answer in the project's semantic cache.
        """
        if not settings.RAG_SEMANTIC_CACHE_ENABLED:
            return

        try:
            client = await self.get_client()
            if not client:
                return

            if query_embedding is None:
                query_embedding = await self.embedding_provider.embed_text(query)

            prefix = self._prefix(workspace_id, project_id)
            entry_id = str(uuid.uuid4())
            entry_key = f"{prefix}:semcache:entry:{entry_id}"
            active_set_key = f"{prefix}:semcache:active_keys"

            payload = {
                "id": entry_id,
                "workspace_id": str(workspace_id),
                "project_id": str(project_id),
                "query": query.strip(),
                "embedding": query_embedding,
                "answer": answer,
                "citations": citations,
                "retrieved_chunks": retrieved_chunks,
                "metadata": metadata or {},
                "created_at": time.time(),
            }

            pipe = client.pipeline()
            pipe.set(entry_key, json.dumps(payload), ex=self.ttl_seconds)
            pipe.sadd(active_set_key, entry_id)
            pipe.expire(active_set_key, self.ttl_seconds + 300)
            await pipe.execute()

            logger.info("Stored semantic cache entry %s for query: '%s'", entry_id, query)
        except Exception as e:
            logger.warning("Redis semantic cache store error: %s", e)
