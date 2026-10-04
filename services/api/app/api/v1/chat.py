from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.services.chat_service import ChatService

router = APIRouter(tags=["Chat & Baseline/Conversational RAG"])
chat_service = ChatService()


def _to_uuid(val: Any) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Student academic query")
    conversation_id: Optional[str] = Field(None, description="Existing conversation to append to")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    document_ids: Optional[List[str]] = Field(None, description="Optional document filter")
    effort: Optional[str] = Field(None, description="Dynamic effort level: 'simple', 'medium', or 'hard'")
    mode: Optional[str] = Field(None, description="Retrieval mode: 'baseline', 'advanced', or 'conversational'")
    rewrite_enabled: Optional[bool] = Field(None, description="Whether to perform LLM contextual query rewriting")
    selected_query: Optional[str] = Field(None, description="Student-selected or edited query override")
    rewrite_accepted: Optional[bool] = Field(None, description="Whether user accepted rewritten query vs original")
    multi_query_enabled: Optional[bool] = Field(None, description="Whether to expand query into multiple retrieval angles")
    decomposition_enabled: Optional[bool] = Field(None, description="Whether to decompose complex question into sub-queries")


class RewritePreviewRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Student query to reformulate")
    conversation_id: Optional[str] = Field(None, description="Conversation context for pronoun resolution")


class RewritePreviewResponse(BaseModel):
    original_query: str
    rewritten_query: str
    was_rewritten: bool
    latency_ms: int
    reason: Optional[str] = None


class ChatCitationResponse(BaseModel):
    id: str
    document_id: str
    document_title: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_path: Optional[str] = ""
    snippet: str
    similarity_score: float
    citation_label: str


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    citations: List[ChatCitationResponse] = []
    created_at: str
    latency_ms: Optional[int] = None
    model: Optional[str] = None
    selected_query: Optional[str] = None
    rewrite_enabled: Optional[bool] = None
    rewrite_accepted: Optional[bool] = None
    multi_query_enabled: Optional[bool] = None
    generated_queries: Optional[List[str]] = None
    cache_hit: Optional[bool] = None
    rag_metadata: Optional[Dict[str, Any]] = None


class ChatQueryResponse(BaseModel):
    conversation_id: str
    message: ChatMessageResponse
    metrics: Dict[str, Any]


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field("New Chat", description="Optional conversation title")


class ConversationItem(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    title: str
    is_pinned: bool
    status: str
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    conversations: List[ConversationItem]
    total: int


class MessageListResponse(BaseModel):
    messages: List[ChatMessageResponse]
    total: int


@router.post(
    "/projects/{project_id}/chat/rewrite",
    response_model=RewritePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview conversational query rewriting before executing retrieval",
)
async def preview_query_rewrite(
    project_id: str,
    payload: RewritePreviewRequest,
    current_user: Any = Depends(get_current_user),
) -> RewritePreviewResponse:
    workspace_id = _to_uuid(getattr(current_user, "workspace_id", None) or current_user["workspace_id"])
    user_id = _to_uuid(getattr(current_user, "id", None) or current_user["user_id"])
    proj_uuid = _to_uuid(project_id)
    conv_uuid = _to_uuid(payload.conversation_id) if payload.conversation_id else None

    result = await chat_service.preview_rewrite(
        workspace_id=workspace_id,
        project_id=proj_uuid,
        user_id=user_id,
        query=payload.query,
        conversation_id=conv_uuid,
    )
    return RewritePreviewResponse(**result)


@router.post(
    "/projects/{project_id}/chat",
    response_model=ChatQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit query to RAG pipeline (conversational, advanced hybrid, or baseline) and receive grounded answer",
)
async def chat_with_project_rag(
    project_id: str,
    payload: ChatQueryRequest,
    current_user: Any = Depends(get_current_user),
) -> ChatQueryResponse:
    workspace_id = _to_uuid(getattr(current_user, "workspace_id", None) or current_user["workspace_id"])
    user_id = _to_uuid(getattr(current_user, "id", None) or current_user["user_id"])
    proj_uuid = _to_uuid(project_id)
    conv_uuid = _to_uuid(payload.conversation_id) if payload.conversation_id else None
    doc_uuids = [_to_uuid(d) for d in payload.document_ids] if payload.document_ids else None

    result = await chat_service.handle_chat_query(
        workspace_id=workspace_id,
        project_id=proj_uuid,
        user_id=user_id,
        query=payload.query,
        conversation_id=conv_uuid,
        top_k=payload.top_k or 5,
        document_ids=doc_uuids,
        effort=payload.effort,
        retrieval_mode=payload.mode,
        rewrite_enabled=payload.rewrite_enabled,
        selected_query=payload.selected_query,
        rewrite_accepted=payload.rewrite_accepted,
        multi_query_enabled=payload.multi_query_enabled,
        decomposition_enabled=payload.decomposition_enabled,
    )
    return ChatQueryResponse(**result)


@router.post(
    "/projects/{project_id}/conversations",
    response_model=ConversationItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new persisted conversation in a project",
)
async def create_project_conversation(
    project_id: str,
    payload: Optional[ConversationCreateRequest] = None,
    current_user: Any = Depends(get_current_user),
) -> ConversationItem:
    workspace_id = _to_uuid(getattr(current_user, "workspace_id", None) or current_user["workspace_id"])
    user_id = _to_uuid(getattr(current_user, "id", None) or current_user["user_id"])
    proj_uuid = _to_uuid(project_id)
    title = payload.title if payload and payload.title else "New Chat"
    conv = await chat_service.create_conversation(
        workspace_id=workspace_id,
        project_id=proj_uuid,
        user_id=user_id,
        title=title,
    )
    return ConversationItem(**conv)


@router.get(
    "/projects/{project_id}/conversations",
    response_model=ConversationListResponse,
    summary="List conversations in a project",
)
async def list_project_conversations(
    project_id: str,
    current_user: Any = Depends(get_current_user),
) -> ConversationListResponse:
    workspace_id = _to_uuid(getattr(current_user, "workspace_id", None) or current_user["workspace_id"])
    proj_uuid = _to_uuid(project_id)
    conversations = await chat_service.list_conversations(
        workspace_id=workspace_id,
        project_id=proj_uuid,
    )
    return ConversationListResponse(
        conversations=[ConversationItem(**c) for c in conversations],
        total=len(conversations),
    )


@router.get(
    "/projects/{project_id}/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    summary="Get conversation history and citations",
)
async def get_conversation_history(
    project_id: str,
    conversation_id: str,
    current_user: Any = Depends(get_current_user),
) -> MessageListResponse:
    workspace_id = _to_uuid(getattr(current_user, "workspace_id", None) or current_user["workspace_id"])
    proj_uuid = _to_uuid(project_id)
    conv_uuid = _to_uuid(conversation_id)
    messages = await chat_service.get_conversation_messages(
        workspace_id=workspace_id,
        project_id=proj_uuid,
        conversation_id=conv_uuid,
    )
    return MessageListResponse(
        messages=[ChatMessageResponse(**m) for m in messages],
        total=len(messages),
    )
