from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    project_id: str
    original_filename: str
    storage_path: str
    mime_type: str
    extension: str
    byte_size: int
    page_count: Optional[int] = None
    checksum: Optional[str] = None
    document_version: int = 1
    ingestion_status: str
    ingestion_error_code: Optional[str] = None
    ingestion_error_message: Optional[str] = None
    parser_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime] = None
    chunk_count: Optional[int] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    job_id: str
    status: str
    message: str = "Document uploaded successfully and queued for background ingestion."


class IngestionJobResponse(BaseModel):
    id: str
    document_id: str
    status: str
    stage: str
    attempt_count: int
    progress_metadata: Dict[str, Any] = {}
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
