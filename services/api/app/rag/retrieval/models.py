from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass
class RetrievedChunk:
    """
    Represents a retrieved document chunk with provenance metadata, similarity score,
    and multi-path hybrid retrieval provenance (dense, lexical, RRF, reranking).
    """
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

    # Phase 7 Provenance Attributes
    dense_score: Optional[float] = None
    dense_rank: Optional[int] = None
    lexical_score: Optional[float] = None
    lexical_rank: Optional[int] = None
    rrf_score: Optional[float] = None
    rerank_score: Optional[float] = None
    retrieval_method: str = "dense"  # "dense" | "lexical" | "hybrid" | "reranked"

    @property
    def document_title(self) -> str:
        return self.document_filename

    @property
    def citation_label(self) -> str:
        return f"[{self.document_filename}, p. {self.page_start}]" if self.page_start else f"[{self.document_filename}]"
