from dataclasses import dataclass
from typing import List, Optional
import uuid


@dataclass
class CitationSource:
    """Metadata representing an attributable source citation for a chunk."""
    document_id: uuid.UUID
    document_filename: str
    chunk_id: uuid.UUID
    page_start: Optional[int]
    page_end: Optional[int]
    slide_number: Optional[int]
    section_path: Optional[str]
    similarity_score: float
    citation_label: str
    snippet: str

    @property
    def document_title(self) -> str:
        return self.document_filename


@dataclass
class BuildContextResult:
    """Assembled prompt context with associated citations."""
    context_text: str
    citations: List[CitationSource]
    total_chars: int

    @property
    def text(self) -> str:
        return self.context_text
