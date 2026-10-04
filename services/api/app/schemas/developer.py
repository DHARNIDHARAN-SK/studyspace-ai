from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# API Key Management Schemas
# ------------------------------------------------------------------------------
class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(
        default=["chat:write", "retrieval:read", "revision:read"],
        description="List of permitted scopes. e.g. chat:write, retrieval:read, revision:read, *",
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=365,
        description="Optional lifetime of key in days. None = no expiration.",
    )


class ApiKeyCreatedResponse(BaseModel):
    """Returned ONLY ONCE upon key creation. Contains full plaintext key."""
    id: str
    workspace_id: str
    name: str
    key_prefix: str
    api_key: str
    scopes: List[str]
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class ApiKeyPublicResponse(BaseModel):
    """Public metadata for existing keys. Secret key is masked."""
    id: str
    workspace_id: str
    name: str
    key_prefix: str
    scopes: List[str]
    status: str
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None


class ApiKeyListResponse(BaseModel):
    keys: List[ApiKeyPublicResponse]
    total: int


# ------------------------------------------------------------------------------
# Developer Programmatic Endpoints Schemas
# ------------------------------------------------------------------------------
class DevChatRequest(BaseModel):
    project_id: str = Field(..., description="Target project ID")
    message: str = Field(..., min_length=1, max_length=5000, description="User prompt")
    conversation_id: Optional[str] = Field(default=None, description="Optional existing conversation")


class DevChatResponse(BaseModel):
    project_id: str
    conversation_id: str
    reply: str
    citations: List[Dict[str, Any]] = []
    model: str
    latency_ms: int
    usage: Dict[str, int] = {}


class DevRetrievalRequest(BaseModel):
    project_id: str = Field(..., description="Target project ID")
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Max chunks to return")


class DevRetrievalChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any] = {}


class DevRetrievalResponse(BaseModel):
    query: str
    results: List[DevRetrievalChunk]
    total: int


class UsageEventItem(BaseModel):
    id: str
    event_type: str
    model_provider: Optional[str] = None
    model_id: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: Optional[int] = None
    status_code: Optional[int] = None
    created_at: datetime


class DevUsageSummaryResponse(BaseModel):
    workspace_id: str
    total_requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    recent_events: List[UsageEventItem] = []
