from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.services.chat_service import ChatService

router = APIRouter(tags=["Chat & Baseline RAG"])
chat_service = ChatService()


class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Student academic query")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Existing conversation to append to")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    document_ids: Optional[List[uuid.UUID]] = Field(None, description="Optional document filter")


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


class ChatQueryResponse(BaseModel):
    conversation_id: str
    message: ChatMessageResponse
    metrics: Dict[str, Any]


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
    "/projects/{project_id}/chat",
    response_model=ChatQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit query to baseline RAG pipeline and receive grounded answer",
)
async def chat_with_project_rag(
    project_id: uuid.UUID,
    payload: ChatQueryRequest,
    current_user: Any = Depends(get_current_user),
) -> ChatQueryResponse:
    workspace_id = uuid.UUID(str(getattr(current_user, "workspace_id", None) or current_user["workspace_id"]))
    user_id = uuid.UUID(str(getattr(current_user, "id", None) or current_user["user_id"]))

    result = await chat_service.handle_chat_query(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
        query=payload.query,
        conversation_id=payload.conversation_id,
        top_k=payload.top_k or 5,
        document_ids=payload.document_ids,
    )
    return ChatQueryResponse(**result)


@router.get(
    "/projects/{project_id}/conversations",
    response_model=ConversationListResponse,
    summary="List conversations in a project",
)
async def list_project_conversations(
    project_id: uuid.UUID,
    current_user: Any = Depends(get_current_user),
) -> ConversationListResponse:
    workspace_id = uuid.UUID(str(getattr(current_user, "workspace_id", None) or current_user["workspace_id"]))
    conversations = await chat_service.list_conversations(
        workspace_id=workspace_id,
        project_id=project_id,
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
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: Any = Depends(get_current_user),
) -> MessageListResponse:
    workspace_id = uuid.UUID(str(getattr(current_user, "workspace_id", None) or current_user["workspace_id"]))
    messages = await chat_service.get_conversation_messages(
        workspace_id=workspace_id,
        project_id=project_id,
        conversation_id=conversation_id,
    )
    return MessageListResponse(
        messages=[ChatMessageResponse(**m) for m in messages],
        total=len(messages),
    )
