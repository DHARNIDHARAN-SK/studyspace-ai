from datetime import datetime, timedelta, timezone
import time
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_key_auth import generate_api_key_pair, hash_api_key
from app.core.logging import logger
from app.db.documents import ensure_workspace_hierarchy
from app.db.models import ApiKey, DocumentChunk, RevisionItem, UsageEvent
from app.db.repository import store
from app.rag.retrieval.hybrid_retriever import HybridRetriever
from app.rag.llm.base import BaseLLMProvider
from app.rag.llm.registry import get_llm_provider
from app.schemas.developer import (
    ApiKeyCreatedResponse,
    ApiKeyPublicResponse,
    DevChatResponse,
    DevRetrievalChunk,
    DevRetrievalResponse,
    DevUsageSummaryResponse,
    UsageEventItem,
)


def _to_uuid(val: Any) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


class DeveloperService:
    """
    Manages developer API keys, usage audit events, rate limit accounting,
    and developer programmatic endpoints with strict tenant isolation.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.retriever = HybridRetriever()
        self.llm = get_llm_provider()

    async def create_api_key(
        self,
        workspace_id: str,
        user_id: str,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None,
    ) -> ApiKeyCreatedResponse:
        key_id = str(uuid.uuid4())
        raw_key, key_prefix, key_hash = generate_api_key_pair()
        created_at = datetime.now(timezone.utc)
        expires_at = (
            created_at + timedelta(days=expires_in_days)
            if expires_in_days is not None
            else None
        )

        record_data = {
            "id": key_id,
            "workspace_id": workspace_id,
            "created_by_user_id": user_id,
            "name": name,
            "key_prefix": key_prefix,
            "key_hash": key_hash,
            "scopes": scopes,
            "rate_limit_policy": {"rpm": 100},
            "status": "active",
            "last_used_at": None,
            "expires_at": expires_at,
            "created_at": created_at,
            "revoked_at": None,
        }

        # Store in database if available
        if self.db is not None:
            try:
                ws_uuid = _to_uuid(workspace_id)
                user_uuid = _to_uuid(user_id)
                k_uuid = _to_uuid(key_id)
                await ensure_workspace_hierarchy(self.db, user_uuid, ws_uuid)

                db_key = ApiKey(
                    id=k_uuid,
                    workspace_id=ws_uuid,
                    created_by_user_id=user_uuid,
                    name=name,
                    key_prefix=key_prefix,
                    key_hash=key_hash,
                    scopes=scopes,
                    rate_limit_policy={"rpm": 100},
                    status="active",
                    expires_at=expires_at,
                    created_at=created_at,
                )
                self.db.add(db_key)
                await self.db.commit()
                await self.db.refresh(db_key)
            except Exception as e:
                logger.warning(f"Failed to persist ApiKey to DB: {e}. Writing to MemoryStore.")
                try:
                    await self.db.rollback()
                except Exception:
                    pass
                store.api_keys[key_id] = record_data
        else:
            store.api_keys[key_id] = record_data

        return ApiKeyCreatedResponse(
            id=key_id,
            workspace_id=workspace_id,
            name=name,
            key_prefix=key_prefix,
            api_key=raw_key,  # Full plaintext returned ONLY on creation
            scopes=scopes,
            status="active",
            created_at=created_at,
            expires_at=expires_at,
        )

    async def list_api_keys(self, workspace_id: str) -> List[ApiKeyPublicResponse]:
        keys: List[ApiKeyPublicResponse] = []
        ws_uuid = _to_uuid(workspace_id)

        if self.db is not None:
            try:
                stmt = (
                    select(ApiKey)
                    .where(ApiKey.workspace_id == ws_uuid)
                    .order_by(desc(ApiKey.created_at))
                )
                result = await self.db.execute(stmt)
                db_keys = result.scalars().all()
                for k in db_keys:
                    keys.append(
                        ApiKeyPublicResponse(
                            id=str(k.id),
                            workspace_id=str(k.workspace_id),
                            name=k.name,
                            key_prefix=k.key_prefix,
                            scopes=k.scopes or [],
                            status=k.status,
                            last_used_at=k.last_used_at,
                            expires_at=k.expires_at,
                            created_at=k.created_at,
                            revoked_at=k.revoked_at,
                        )
                    )
                if keys:
                    return keys
            except Exception as e:
                logger.warning(f"Failed to query DB for API keys: {e}. Falling back to MemoryStore.")
                try:
                    await self.db.rollback()
                except Exception:
                    pass

        # Memory store fallback
        for k_id, item in store.api_keys.items():
            if str(item.get("workspace_id")) == str(workspace_id):
                keys.append(
                    ApiKeyPublicResponse(
                        id=k_id,
                        workspace_id=str(item["workspace_id"]),
                        name=item["name"],
                        key_prefix=item["key_prefix"],
                        scopes=item.get("scopes", []),
                        status=item.get("status", "active"),
                        last_used_at=item.get("last_used_at"),
                        expires_at=item.get("expires_at"),
                        created_at=item.get("created_at", datetime.now(timezone.utc)),
                        revoked_at=item.get("revoked_at"),
                    )
                )

        keys.sort(key=lambda x: x.created_at, reverse=True)
        return keys

    async def revoke_api_key(self, workspace_id: str, key_id: str) -> bool:
        now_utc = datetime.now(timezone.utc)
        found = False
        ws_uuid = _to_uuid(workspace_id)
        k_uuid = _to_uuid(key_id)

        if self.db is not None:
            try:
                stmt = (
                    update(ApiKey)
                    .where(ApiKey.id == k_uuid, ApiKey.workspace_id == ws_uuid)
                    .values(status="revoked", revoked_at=now_utc)
                )
                res = await self.db.execute(stmt)
                await self.db.commit()
                if res.rowcount > 0:
                    found = True
            except Exception as e:
                logger.warning(f"Failed to revoke key in DB: {e}. Falling back to MemoryStore.")
                try:
                    await self.db.rollback()
                except Exception:
                    pass

        if key_id in store.api_keys:
            if str(store.api_keys[key_id].get("workspace_id")) == str(workspace_id):
                store.api_keys[key_id]["status"] = "revoked"
                store.api_keys[key_id]["revoked_at"] = now_utc
                found = True

        return found

    async def record_usage(
        self,
        workspace_id: str,
        api_key_id: Optional[str],
        event_type: str,
        model_provider: Optional[str] = None,
        model_id: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: Optional[int] = None,
        status_code: int = 200,
    ) -> None:
        total_tokens = prompt_tokens + completion_tokens
        event_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        event_data = {
            "id": event_id,
            "workspace_id": workspace_id,
            "api_key_id": api_key_id,
            "event_type": event_type,
            "model_provider": model_provider,
            "model_id": model_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency_ms": latency_ms,
            "status_code": status_code,
            "created_at": created_at,
        }

        if self.db is not None:
            try:
                ws_uuid = _to_uuid(workspace_id)
                ev_uuid = _to_uuid(event_id)
                k_uuid = _to_uuid(api_key_id) if api_key_id else None
                db_event = UsageEvent(
                    id=ev_uuid,
                    workspace_id=ws_uuid,
                    api_key_id=k_uuid,
                    event_type=event_type,
                    model_provider=model_provider,
                    model_id=model_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    status_code=status_code,
                    created_at=created_at,
                )
                self.db.add(db_event)
                await self.db.commit()
                return
            except Exception as e:
                logger.warning(f"Failed to record usage in DB: {e}. Writing to MemoryStore.")
                try:
                    await self.db.rollback()
                except Exception:
                    pass

        store.usage_events.append(event_data)

    async def get_usage_summary(self, workspace_id: str) -> DevUsageSummaryResponse:
        events: List[UsageEventItem] = []
        total_requests = 0
        prompt_tokens = 0
        completion_tokens = 0
        ws_uuid = _to_uuid(workspace_id)

        if self.db is not None:
            try:
                stmt = (
                    select(UsageEvent)
                    .where(UsageEvent.workspace_id == ws_uuid)
                    .order_by(desc(UsageEvent.created_at))
                    .limit(50)
                )
                res = await self.db.execute(stmt)
                db_events = res.scalars().all()
                for ev in db_events:
                    events.append(
                        UsageEventItem(
                            id=str(ev.id),
                            event_type=ev.event_type,
                            model_provider=ev.model_provider,
                            model_id=ev.model_id,
                            prompt_tokens=ev.prompt_tokens,
                            completion_tokens=ev.completion_tokens,
                            total_tokens=ev.total_tokens,
                            latency_ms=ev.latency_ms,
                            status_code=ev.status_code,
                            created_at=ev.created_at,
                        )
                    )
                    total_requests += 1
                    prompt_tokens += ev.prompt_tokens
                    completion_tokens += ev.completion_tokens

                if total_requests > 0:
                    return DevUsageSummaryResponse(
                        workspace_id=workspace_id,
                        total_requests=total_requests,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                        recent_events=events,
                    )
            except Exception as e:
                logger.warning(f"Failed to query DB usage summary: {e}. Checking MemoryStore.")
                try:
                    await self.db.rollback()
                except Exception:
                    pass

        # Memory store fallback
        for ev in reversed(store.usage_events):
            if str(ev.get("workspace_id")) == str(workspace_id):
                events.append(
                    UsageEventItem(
                        id=ev["id"],
                        event_type=ev["event_type"],
                        model_provider=ev.get("model_provider"),
                        model_id=ev.get("model_id"),
                        prompt_tokens=ev.get("prompt_tokens", 0),
                        completion_tokens=ev.get("completion_tokens", 0),
                        total_tokens=ev.get("total_tokens", 0),
                        latency_ms=ev.get("latency_ms"),
                        status_code=ev.get("status_code", 200),
                        created_at=ev.get("created_at", datetime.now(timezone.utc)),
                    )
                )
                total_requests += 1
                prompt_tokens += ev.get("prompt_tokens", 0)
                completion_tokens += ev.get("completion_tokens", 0)
                if len(events) >= 50:
                    break

        return DevUsageSummaryResponse(
            workspace_id=workspace_id,
            total_requests=total_requests,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            recent_events=events,
        )

    async def dev_retrieve(
        self,
        workspace_id: str,
        project_id: str,
        query: str,
        top_k: int = 5,
    ) -> DevRetrievalResponse:
        ws_uuid = _to_uuid(workspace_id)
        proj_uuid = _to_uuid(project_id)
        try:
            results = await self.retriever.retrieve(
                query=query,
                workspace_id=ws_uuid,
                project_id=proj_uuid,
                final_top_k=top_k,
                session=self.db,
            )
        except Exception as e:
            logger.warning(f"Retrieval failed in dev_retrieve: {e}. Returning empty candidate list.")
            results = []

        chunks = [
            DevRetrievalChunk(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                content=r.content,
                similarity_score=float(r.score),
                metadata=r.metadata,
            )
            for r in results
        ]

        return DevRetrievalResponse(
            query=query,
            results=chunks,
            total=len(chunks),
        )

    async def dev_chat(
        self,
        workspace_id: str,
        project_id: str,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> DevChatResponse:
        t0 = time.time()
        conv_id = conversation_id or str(uuid.uuid4())
        ws_uuid = _to_uuid(workspace_id)
        proj_uuid = _to_uuid(project_id)

        # Retrieve relevant context
        try:
            context_chunks = await self.retriever.retrieve(
                query=message,
                workspace_id=ws_uuid,
                project_id=proj_uuid,
                final_top_k=4,
                session=self.db,
            )
        except Exception as e:
            logger.warning(f"Context retrieval failed in dev_chat: {e}. Proceeding without context.")
            context_chunks = []

        citations = []
        context_blocks = []
        for i, c in enumerate(context_chunks):
            context_blocks.append(f"[{i+1}] {c.content}")
            citations.append({
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "score": float(c.score),
            })

        context_text = "\n\n".join(context_blocks)
        system_prompt = (
            "You are the StudySpace AI Developer Assistant. "
            "Answer the developer's question accurately using ONLY the provided course reference context. "
            "Cite sources using [1], [2] when referencing information. If the answer cannot be found, state so clearly."
        )

        user_prompt = f"Context:\n{context_text}\n\nQuestion:\n{message}" if context_text else message

        try:
            reply = await self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=600,
            )
        except Exception as e:
            logger.warning(f"LLM generation failed in dev_chat: {e}. Generating grounded fallback response.")
            reply = (
                f"Based on project knowledge for '{project_id}': "
                f"Context contains {len(context_chunks)} reference items related to your query."
            )

        latency_ms = int((time.time() - t0) * 1000)
        if hasattr(reply, "content"):
            reply_text = str(reply.content)
            model_id = getattr(reply, "model", getattr(self.llm, "model_id", "local-llm"))
            c_tokens = getattr(reply, "completion_tokens", None) or (len(reply_text) // 4)
            p_tokens = getattr(reply, "prompt_tokens", None) or (len(user_prompt) // 4)
        else:
            reply_text = str(reply)
            model_id = getattr(self.llm, "model_id", "local-llm")
            c_tokens = len(reply_text) // 4
            p_tokens = len(user_prompt) // 4

        return DevChatResponse(
            project_id=project_id,
            conversation_id=conv_id,
            reply=reply_text,
            citations=citations,
            model=model_id,
            latency_ms=latency_ms,
            usage={"prompt_tokens": p_tokens, "completion_tokens": c_tokens, "total_tokens": p_tokens + c_tokens},
        )
