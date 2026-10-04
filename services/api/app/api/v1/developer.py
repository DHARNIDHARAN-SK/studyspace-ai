from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_key_auth import ApiKeyContext, get_api_key
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db_optional
from app.schemas.developer import (
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    DevChatRequest,
    DevChatResponse,
    DevRetrievalRequest,
    DevRetrievalResponse,
    DevUsageSummaryResponse,
)
from app.schemas.study import RevisionListResponse
from app.services.developer_service import DeveloperService
from app.services.study_service import StudyService

# ------------------------------------------------------------------------------
# 1. Developer Management Router (Web Dashboard, JWT Authenticated)
# ------------------------------------------------------------------------------
developer_router = APIRouter(prefix="/developer", tags=["Developer Platform"])


@developer_router.post("/keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Create a new API key for the current workspace.
    The plaintext secret is returned ONLY ONCE in the response.
    """
    svc = DeveloperService(db=db)
    return await svc.create_api_key(
        workspace_id=user.workspace_id,
        user_id=user.id,
        name=payload.name,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
    )


@developer_router.get("/keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    List all API keys for the current workspace. Secret keys are masked.
    """
    svc = DeveloperService(db=db)
    keys = await svc.list_api_keys(workspace_id=user.workspace_id)
    return ApiKeyListResponse(keys=keys, total=len(keys))


@developer_router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Revoke an API key immediately. Revoked keys cannot be restored.
    """
    svc = DeveloperService(db=db)
    success = await svc.revoke_api_key(workspace_id=user.workspace_id, key_id=key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key '{key_id}' not found in current workspace.",
        )


@developer_router.get("/usage", response_model=DevUsageSummaryResponse)
async def get_usage_summary(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Retrieve audit and usage stats for the current workspace.
    """
    svc = DeveloperService(db=db)
    return await svc.get_usage_summary(workspace_id=user.workspace_id)


# ------------------------------------------------------------------------------
# 2. Developer Programmatic Router (Secured strictly via API Key)
# ------------------------------------------------------------------------------
dev_programmatic_router = APIRouter(prefix="/dev", tags=["Developer Programmatic API"])


@dev_programmatic_router.post("/chat", response_model=DevChatResponse)
async def dev_chat_endpoint(
    payload: DevChatRequest,
    api_ctx: ApiKeyContext = Security(get_api_key, scopes=["chat:write"]),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Programmatic chat inference scoped to the API key's workspace and requested project.
    Requires scope 'chat:write'.
    """
    svc = DeveloperService(db=db)
    resp = await svc.dev_chat(
        workspace_id=api_ctx.workspace_id,
        project_id=payload.project_id,
        message=payload.message,
        conversation_id=payload.conversation_id,
    )

    # Record usage event
    await svc.record_usage(
        workspace_id=api_ctx.workspace_id,
        api_key_id=api_ctx.key_id,
        event_type="chat",
        model_provider="ollama",
        model_id=resp.model,
        prompt_tokens=resp.usage.get("prompt_tokens", 0),
        completion_tokens=resp.usage.get("completion_tokens", 0),
        latency_ms=resp.latency_ms,
        status_code=200,
    )

    return resp


@dev_programmatic_router.post("/retrieve", response_model=DevRetrievalResponse)
async def dev_retrieve_endpoint(
    payload: DevRetrievalRequest,
    api_ctx: ApiKeyContext = Security(get_api_key, scopes=["retrieval:read"]),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Programmatic hybrid retrieval scoped to the API key's workspace and requested project.
    Requires scope 'retrieval:read'.
    """
    svc = DeveloperService(db=db)
    resp = await svc.dev_retrieve(
        workspace_id=api_ctx.workspace_id,
        project_id=payload.project_id,
        query=payload.query,
        top_k=payload.top_k,
    )

    # Record usage event
    await svc.record_usage(
        workspace_id=api_ctx.workspace_id,
        api_key_id=api_ctx.key_id,
        event_type="retrieval",
        prompt_tokens=len(payload.query) // 4,
        completion_tokens=0,
        latency_ms=10,
        status_code=200,
    )

    return resp


@dev_programmatic_router.get(
    "/projects/{project_id}/revision",
    response_model=RevisionListResponse,
)
async def dev_list_revision_items(
    project_id: str,
    status_filter: Optional[str] = None,
    api_ctx: ApiKeyContext = Security(get_api_key, scopes=["revision:read"]),
    db: Optional[AsyncSession] = Depends(get_db_optional),
):
    """
    Programmatic access to project revision checklist.
    Requires scope 'revision:read'.
    """
    user_uuid = uuid.UUID(api_ctx.created_by_user_id) if isinstance(api_ctx.created_by_user_id, str) and len(api_ctx.created_by_user_id) == 36 else uuid.uuid5(uuid.NAMESPACE_DNS, str(api_ctx.created_by_user_id))
    ws_uuid = uuid.UUID(api_ctx.workspace_id) if isinstance(api_ctx.workspace_id, str) and len(api_ctx.workspace_id) == 36 else uuid.uuid5(uuid.NAMESPACE_DNS, str(api_ctx.workspace_id))
    proj_uuid = uuid.UUID(project_id) if isinstance(project_id, str) and len(project_id) == 36 else uuid.uuid5(uuid.NAMESPACE_DNS, str(project_id))

    svc = StudyService()
    resp = await svc.list_revision_items(
        user_id=user_uuid,
        workspace_id=ws_uuid,
        project_id=proj_uuid,
        db=db,
    )

    # Record usage event
    dev_svc = DeveloperService(db=db)
    await dev_svc.record_usage(
        workspace_id=api_ctx.workspace_id,
        api_key_id=api_ctx.key_id,
        event_type="revision_list",
        prompt_tokens=0,
        completion_tokens=len(resp.items),
        latency_ms=5,
        status_code=200,
    )

    return resp
