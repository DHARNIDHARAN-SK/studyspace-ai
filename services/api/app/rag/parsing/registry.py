from typing import Dict, Type
from pathlib import Path

from app.core.errors import AppError
from app.rag.parsing.base import BaseParser
from app.rag.parsing.pdf_parser import PDFParser
from app.rag.parsing.docx_parser import DocxParser
from app.rag.parsing.pptx_parser import PPTXParser
from app.rag.parsing.text_parser import TextParser


class UnsupportedParserFormatError(AppError):
    def __init__(self, extension: str):
        supported = ", ".join(SUPPORTED_PARSER_EXTENSIONS.keys())
        super().__init__(
            message=f"No parser available for format '{extension}'. Supported formats: {supported}.",
            code="UNSUPPORTED_PARSER_FORMAT",
            status_code=415,
            action=f"Please upload one of the supported academic file types: {supported}",
        )


PARSER_REGISTRY: Dict[str, Type[BaseParser]] = {
    ".pdf": PDFParser,
    ".docx": DocxParser,
    ".pptx": PPTXParser,
    ".txt": TextParser,
    ".md": TextParser,
}

SUPPORTED_PARSER_EXTENSIONS = {ext: cls for ext, cls in PARSER_REGISTRY.items()}


def get_parser_for_filename(filename: str) -> BaseParser:
    """
    Resolves and instantiates the appropriate parser for a given filename based on its extension.
    """
    ext = Path(filename).suffix.lower()
    parser_cls = PARSER_REGISTRY.get(ext)
    if not parser_cls:
        raise UnsupportedParserFormatError(ext)
    return parser_cls()
