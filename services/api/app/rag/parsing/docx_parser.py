import io
from typing import List, Optional
import docx

from app.core.errors import AppError
from app.core.logging import logger
from app.rag.parsing.base import BaseParser, ParsedBlock, ParsedDocument


class DocxParsingError(AppError):
    def __init__(self, message: str, code: str = "DOCX_PARSING_FAILED", status_code: int = 400):
        super().__init__(message=message, code=code, status_code=status_code)


class DocxParser(BaseParser):
    """
    Parser for Microsoft Word (.docx) documents.
    Extracts heading hierarchy (Heading 1/2/3), paragraphs, bullet lists, and tables.
    Preserves section_path provenance for academic citation.
    """

    @property
    def parser_name(self) -> str:
        return "python-docx"

    @property
    def parser_version(self) -> str:
        return getattr(docx, "__version__", "1.1.0")

    def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
        except Exception as exc:
            logger.error("Failed to parse DOCX document '%s': %s", filename, exc)
            raise DocxParsingError(f"Corrupted or invalid DOCX document: {filename}")

        blocks: List[ParsedBlock] = []
        heading_stack: List[str] = []
        current_heading: Optional[str] = None

        # 1. Parse paragraphs and headings
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            style_name = para.style.name if para.style else ""
            lower_style = style_name.lower()

            if "heading 1" in lower_style:
                heading_stack = [text]
                current_heading = text
                blocks.append(
                    ParsedBlock(
                        content=text,
                        block_type="heading",
                        heading=current_heading,
                        section_path=" > ".join(heading_stack),
                        metadata={"style": style_name, "level": 1},
                    )
                )
            elif "heading 2" in lower_style:
                heading_stack = heading_stack[:1] + [text]
                current_heading = text
                blocks.append(
                    ParsedBlock(
                        content=text,
                        block_type="heading",
                        heading=current_heading,
                        section_path=" > ".join(heading_stack),
                        metadata={"style": style_name, "level": 2},
                    )
                )
            elif "heading 3" in lower_style:
                heading_stack = heading_stack[:2] + [text]
                current_heading = text
                blocks.append(
                    ParsedBlock(
                        content=text,
                        block_type="heading",
                        heading=current_heading,
                        section_path=" > ".join(heading_stack),
                        metadata={"style": style_name, "level": 3},
                    )
                )
            elif "list" in lower_style or "bullet" in lower_style:
                blocks.append(
                    ParsedBlock(
                        content=text,
                        block_type="list_item",
                        heading=current_heading,
                        section_path=" > ".join(heading_stack) if heading_stack else None,
                        metadata={"style": style_name},
                    )
                )
            else:
                blocks.append(
                    ParsedBlock(
                        content=text,
                        block_type="paragraph",
                        heading=current_heading,
                        section_path=" > ".join(heading_stack) if heading_stack else None,
                        metadata={"style": style_name},
                    )
                )

        # 2. Parse tables
        for table_idx, table in enumerate(doc.tables):
            table_lines: List[str] = []
            for row in table.rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                # Filter out redundant consecutive duplicate cells resulting from merged cells
                cleaned_cells = []
                for cell in cells:
                    if not cleaned_cells or cell != cleaned_cells[-1]:
                        cleaned_cells.append(cell)
                if any(cleaned_cells):
                    table_lines.append(" | ".join(cleaned_cells))

            if table_lines:
                table_content = "\n".join(table_lines)
                blocks.append(
                    ParsedBlock(
                        content=table_content,
                        block_type="table",
                        heading=current_heading,
                        section_path=" > ".join(heading_stack) if heading_stack else None,
                        metadata={"table_index": table_idx + 1, "row_count": len(table.rows)},
                    )
                )

        # Extract core document metadata
        metadata = {}
        try:
            core_props = doc.core_properties
            if core_props.title:
                metadata["title"] = core_props.title
            if core_props.author:
                metadata["author"] = core_props.author
            if core_props.subject:
                metadata["subject"] = core_props.subject
        except Exception:
            pass

        return ParsedDocument(
            filename=filename,
            extension=".docx",
            page_count=None,  # Word files do not define native page counts without pagination rendering
            blocks=blocks,
            metadata=metadata,
        )
