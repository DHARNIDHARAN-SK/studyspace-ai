from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk with provenance metadata and similarity score."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str
    workspace_id: uuid.UUID
    project_id: uuid.UUID
    chunk_index: int
    content: str
    token_count: Optional[int]
    page_start: Optional[int]
    page_end: Optional[int]
    slide_number: Optional[int]
    slide_title: Optional[str]
    section_path: Optional[str]
    heading: Optional[str]
    similarity_score: float
