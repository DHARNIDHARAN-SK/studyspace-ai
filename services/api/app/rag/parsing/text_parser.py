import re
from typing import List, Optional

from app.core.errors import AppError
from app.rag.parsing.base import BaseParser, ParsedBlock, ParsedDocument


class TextParsingError(AppError):
    def __init__(self, message: str, code: str = "TEXT_PARSING_FAILED", status_code: int = 400):
        super().__init__(message=message, code=code, status_code=status_code)


class TextParser(BaseParser):
    """
    Parser for plain text (.txt) and Markdown (.md) documents.
    Preserves heading hierarchies, lists, code fences, and line numbering.
    """

    @property
    def parser_name(self) -> str:
        return "text-markdown-parser"

    @property
    def parser_version(self) -> str:
        return "1.0.0"

    def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        # Decode utf-8 with fallback to latin-1
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = file_bytes.decode("latin-1")
            except Exception as exc:
                raise TextParsingError(f"Could not decode text encoding for {filename}: {exc}")

        is_markdown = filename.lower().endswith(".md")
        lines = content.splitlines()

        if not lines or not content.strip():
            return ParsedDocument(
                filename=filename,
                extension=".md" if is_markdown else ".txt",
                page_count=1,
                blocks=[],
            )

        blocks: List[ParsedBlock] = []

        if is_markdown:
            blocks = self._parse_markdown(lines)
        else:
            blocks = self._parse_plaintext(lines)

        return ParsedDocument(
            filename=filename,
            extension=".md" if is_markdown else ".txt",
            page_count=max(1, len(lines) // 50),  # Approximate synthetic pages for citation UI (~50 lines/page)
            blocks=blocks,
            metadata={"line_count": len(lines), "is_markdown": is_markdown},
        )

    def _parse_markdown(self, lines: List[str]) -> List[ParsedBlock]:
        blocks: List[ParsedBlock] = []
        heading_stack: List[str] = []
        current_heading: Optional[str] = None

        in_code_block = False
        code_buffer: List[str] = []
        code_start_line = 0

        paragraph_buffer: List[str] = []
        para_start_line = 0

        for line_idx, raw_line in enumerate(lines):
            line_num = line_idx + 1
            line = raw_line.rstrip()

            # Handle code fence
            if line.strip().startswith("```"):
                if in_code_block:
                    # Closing code block
                    code_buffer.append(line)
                    blocks.append(
                        ParsedBlock(
                            content="\n".join(code_buffer),
                            block_type="code",
                            heading=current_heading,
                            section_path=" > ".join(heading_stack) if heading_stack else None,
                            line_start=code_start_line,
                            line_end=line_num,
                        )
                    )
                    code_buffer = []
                    in_code_block = False
                    continue
                else:
                    # Opening code block
                    if paragraph_buffer:
                        blocks.append(
                            ParsedBlock(
                                content=" ".join(paragraph_buffer),
                                block_type="paragraph",
                                heading=current_heading,
                                section_path=" > ".join(heading_stack) if heading_stack else None,
                                line_start=para_start_line,
                                line_end=line_num - 1,
                            )
                        )
                        paragraph_buffer = []

                    in_code_block = True
                    code_start_line = line_num
                    code_buffer = [line]
                    continue

            if in_code_block:
                code_buffer.append(line)
                continue

            # Heading detection
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
            if heading_match:
                if paragraph_buffer:
                    blocks.append(
                        ParsedBlock(
                            content=" ".join(paragraph_buffer),
                            block_type="paragraph",
                            heading=current_heading,
                            section_path=" > ".join(heading_stack) if heading_stack else None,
                            line_start=para_start_line,
                            line_end=line_num - 1,
                        )
                    )
                    paragraph_buffer = []

                level = len(heading_match.group(1))
                h_text = heading_match.group(2).strip()

                # Adjust heading stack according to depth
                heading_stack = heading_stack[: level - 1] + [h_text]
                current_heading = h_text
                blocks.append(
                    ParsedBlock(
                        content=h_text,
                        block_type="heading",
                        heading=current_heading,
                        section_path=" > ".join(heading_stack),
                        line_start=line_num,
                        line_end=line_num,
                        metadata={"level": level},
                    )
                )
                continue

            # Blank line flushes paragraph
            if not line.strip():
                if paragraph_buffer:
                    blocks.append(
                        ParsedBlock(
                            content=" ".join(paragraph_buffer),
                            block_type="paragraph",
                            heading=current_heading,
                            section_path=" > ".join(heading_stack) if heading_stack else None,
                            line_start=para_start_line,
                            line_end=line_num - 1,
                        )
                    )
                    paragraph_buffer = []
                continue

            # List items
            if re.match(r"^(\*|-|\+|\d+\.)\s+", line.strip()):
                if paragraph_buffer:
                    blocks.append(
                        ParsedBlock(
                            content=" ".join(paragraph_buffer),
                            block_type="paragraph",
                            heading=current_heading,
                            section_path=" > ".join(heading_stack) if heading_stack else None,
                            line_start=para_start_line,
                            line_end=line_num - 1,
                        )
                    )
                    paragraph_buffer = []

                blocks.append(
                    ParsedBlock(
                        content=line.strip(),
                        block_type="list_item",
                        heading=current_heading,
                        section_path=" > ".join(heading_stack) if heading_stack else None,
                        line_start=line_num,
                        line_end=line_num,
                    )
                )
                continue

            # Accumulate normal text into paragraph
            if not paragraph_buffer:
                para_start_line = line_num
            paragraph_buffer.append(line.strip())

        # Flush trailing paragraph or code block
        if in_code_block and code_buffer:
            blocks.append(
                ParsedBlock(
                    content="\n".join(code_buffer),
                    block_type="code",
                    heading=current_heading,
                    section_path=" > ".join(heading_stack) if heading_stack else None,
                    line_start=code_start_line,
                    line_end=len(lines),
                )
            )
        elif paragraph_buffer:
            blocks.append(
                ParsedBlock(
                    content=" ".join(paragraph_buffer),
                    block_type="paragraph",
                    heading=current_heading,
                    section_path=" > ".join(heading_stack) if heading_stack else None,
                    line_start=para_start_line,
                    line_end=len(lines),
                )
            )

        return blocks

    def _parse_plaintext(self, lines: List[str]) -> List[ParsedBlock]:
        blocks: List[ParsedBlock] = []
        paragraph_buffer: List[str] = []
        para_start_line = 0

        for line_idx, raw_line in enumerate(lines):
            line_num = line_idx + 1
            line = raw_line.strip()

            if not line:
                if paragraph_buffer:
                    blocks.append(
                        ParsedBlock(
                            content=" ".join(paragraph_buffer),
                            block_type="paragraph",
                            line_start=para_start_line,
                            line_end=line_num - 1,
                        )
                    )
                    paragraph_buffer = []
                continue

            if not paragraph_buffer:
                para_start_line = line_num
            paragraph_buffer.append(line)

        if paragraph_buffer:
            blocks.append(
                ParsedBlock(
                    content=" ".join(paragraph_buffer),
                    block_type="paragraph",
                    line_start=para_start_line,
                    line_end=len(lines),
                )
            )

        return blocks
