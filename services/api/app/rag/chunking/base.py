from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RawChunk(BaseModel):
    """
    In-memory representation of a chunk before persistence into the database.
    Matches SQLAlchemy DocumentChunk model schema.
    """
    chunk_index: int
    content: str
    token_count: int
    content_hash: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    slide_number: Optional[int] = None
    slide_title: Optional[str] = None
    section_path: Optional[str] = None
    heading: Optional[str] = None
    source_offsets: Dict[str, Any] = Field(default_factory=dict)
