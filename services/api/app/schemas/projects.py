from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, max_length=500, description="Optional project description")
    subject: Optional[str] = Field(None, max_length=100, description="Academic subject or course code")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    subject: Optional[str] = Field(None, max_length=100)
    is_archived: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    subject: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
