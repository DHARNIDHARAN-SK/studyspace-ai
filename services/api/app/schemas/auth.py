from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    workspace_id: str
    workspace_name: str
    created_at: datetime
    updated_at: datetime


class ProvisionRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
