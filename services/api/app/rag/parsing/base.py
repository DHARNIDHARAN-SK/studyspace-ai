from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ParsedBlock(BaseModel):
    """
    Atomic structural content block extracted from a source document.
    Maintains fine-grained provenance for future academic citations.
    """
    content: str
    block_type: str = "paragraph"  # 'heading', 'paragraph', 'table', 'slide_notes', 'code', 'list_item'
    page_number: Optional[int] = None      # 1-indexed page number (for PDF / multi-page doc)
    slide_number: Optional[int] = None     # 1-indexed slide number (for PPTX)
    slide_title: Optional[str] = None      # Title of the slide (for PPTX)
    heading: Optional[str] = None          # Closest contextual heading
    section_path: Optional[str] = None     # Hierarchical section path (e.g. "1. Overview / 1.1 Goals")
    line_start: Optional[int] = None       # Source line start (for TXT / MD)
    line_end: Optional[int] = None         # Source line end
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    """
    Structured intermediate representation of a parsed document before chunking.
    """
    filename: str
    extension: str
    page_count: Optional[int] = None
    slide_count: Optional[int] = None
    blocks: List[ParsedBlock] = Field(default_factory=list)
    is_scanned: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def total_text_length(self) -> int:
        return sum(len(b.content) for b in self.blocks)


class BaseParser(ABC):
    """Abstract base class for all StudySpace AI document format parsers."""

    @property
    @abstractmethod
    def parser_name(self) -> str:
        """Name of the parser implementation (e.g., 'pypdf', 'python-docx')."""
        pass

    @property
    @abstractmethod
    def parser_version(self) -> str:
        """Version string of the parser."""
        pass

    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        """Synchronously parses raw file bytes into structured ParsedDocument."""
        pass
