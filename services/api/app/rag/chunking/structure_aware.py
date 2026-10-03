import hashlib
import re
from typing import List, Optional

from app.core.logging import logger
from app.rag.chunking.base import RawChunk
from app.rag.parsing.base import ParsedBlock, ParsedDocument


class StructureAwareChunker:
    """
    Structure-aware chunker adhering to StudySpace AI Master Architecture Section 6.2.
    Respects:
      - Slide boundaries (never blends across slides)
      - Page boundaries (tracks exact page_start and page_end)
      - Heading and section hierarchies (keeps heading attached to context)
      - Paragraph and sentence boundaries
    Discards empty or trivial whitespace chunks and computes deterministic SHA-256 digests.
    """

    def __init__(
        self,
        target_chunk_size: int = 1000,
        chunk_overlap: int = 150,
        min_chunk_size: int = 50,
        max_chunk_size: int = 1600,
    ):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate (~4 characters per token)."""
        return max(1, len(text) // 4)

    def _hash_content(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def chunk_document(self, doc: ParsedDocument) -> List[RawChunk]:
        """
        Transforms a ParsedDocument into a sequence of structured, provenance-preserving chunks.
        """
        if not doc.blocks:
            logger.info("Parsed document '%s' contains no blocks to chunk.", doc.filename)
            return []

        # If document is a presentation, chunk slide-by-slide
        if doc.extension == ".pptx" or doc.slide_count is not None:
            return self._chunk_presentation(doc)

        # For PDFs and text documents, chunk hierarchically respecting sections and pages
        return self._chunk_hierarchical(doc)

    def _chunk_presentation(self, doc: ParsedDocument) -> List[RawChunk]:
        """Chunks presentations strictly preserving slide boundaries."""
        chunks: List[RawChunk] = []
        chunk_idx = 0

        # Group blocks by slide number
        slide_map: dict[int, List[ParsedBlock]] = {}
        for block in doc.blocks:
            slide_no = block.slide_number or 1
            slide_map.setdefault(slide_no, []).append(block)

        for slide_no in sorted(slide_map.keys()):
            blocks = slide_map[slide_no]
            slide_title = blocks[0].slide_title if blocks else None

            # Combine all non-empty text blocks on the slide
            slide_texts: List[str] = []
            for b in blocks:
                content = b.content.strip()
                if content and (not slide_texts or content != slide_texts[-1]):
                    slide_texts.append(content)

            full_slide_text = "\n\n".join(slide_texts).strip()
            if not full_slide_text:
                continue

            # If slide text is within max size, keep it as a single coherent chunk
            if len(full_slide_text) <= self.max_chunk_size:
                chunks.append(
                    RawChunk(
                        chunk_index=chunk_idx,
                        content=full_slide_text,
                        token_count=self._estimate_tokens(full_slide_text),
                        content_hash=self._hash_content(full_slide_text),
                        slide_number=slide_no,
                        slide_title=slide_title,
                        section_path=f"Slide {slide_no}: {slide_title}" if slide_title else f"Slide {slide_no}",
                        heading=slide_title,
                        source_offsets={"slide_number": slide_no, "char_length": len(full_slide_text)},
                    )
                )
                chunk_idx += 1
            else:
                # Large slide: split across sentences with overlap
                sub_chunks = self._split_text_with_overlap(full_slide_text)
                for sc in sub_chunks:
                    chunks.append(
                        RawChunk(
                            chunk_index=chunk_idx,
                            content=sc,
                            token_count=self._estimate_tokens(sc),
                            content_hash=self._hash_content(sc),
                            slide_number=slide_no,
                            slide_title=slide_title,
                            section_path=f"Slide {slide_no}: {slide_title}" if slide_title else f"Slide {slide_no}",
                            heading=slide_title,
                            source_offsets={"slide_number": slide_no, "char_length": len(sc)},
                        )
                    )
                    chunk_idx += 1

        logger.info("Chunked presentation '%s' into %d slide-aligned chunks.", doc.filename, len(chunks))
        return chunks

    def _chunk_hierarchical(self, doc: ParsedDocument) -> List[RawChunk]:
        """
        Chunks documents respecting sections, page boundaries, and paragraphs.
        """
        chunks: List[RawChunk] = []
        chunk_idx = 0

        current_buffer: List[str] = []
        current_len = 0
        current_page_start: Optional[int] = None
        current_page_end: Optional[int] = None
        current_heading: Optional[str] = None
        current_section: Optional[str] = None

        def flush_chunk():
            nonlocal chunk_idx, current_buffer, current_len, current_page_start, current_page_end, current_heading, current_section
            if not current_buffer:
                return

            text = "\n\n".join(current_buffer).strip()
            if len(text) >= self.min_chunk_size:
                chunks.append(
                    RawChunk(
                        chunk_index=chunk_idx,
                        content=text,
                        token_count=self._estimate_tokens(text),
                        content_hash=self._hash_content(text),
                        page_start=current_page_start,
                        page_end=current_page_end or current_page_start,
                        section_path=current_section,
                        heading=current_heading,
                        source_offsets={
                            "page_start": current_page_start,
                            "page_end": current_page_end or current_page_start,
                            "char_length": len(text),
                        },
                    )
                )
                chunk_idx += 1

            current_buffer = []
            current_len = 0
            current_page_start = None
            current_page_end = None

        for block in doc.blocks:
            text = block.content.strip()
            if not text:
                continue

            # If block is a major heading and buffer already has substantial content, flush buffer
            if block.block_type == "heading" and current_len >= self.min_chunk_size:
                flush_chunk()
                current_heading = block.heading or text
                current_section = block.section_path or text

            # Update heading/section context
            if block.heading:
                current_heading = block.heading
            if block.section_path:
                current_section = block.section_path

            # Update page range
            if block.page_number:
                if current_page_start is None:
                    current_page_start = block.page_number
                current_page_end = block.page_number

            # Check if block itself exceeds max chunk size (e.g. huge continuous paragraph)
            if len(text) > self.max_chunk_size:
                flush_chunk()
                sub_splits = self._split_text_with_overlap(text)
                for split_text in sub_splits:
                    if len(split_text) >= self.min_chunk_size:
                        chunks.append(
                            RawChunk(
                                chunk_index=chunk_idx,
                                content=split_text,
                                token_count=self._estimate_tokens(split_text),
                                content_hash=self._hash_content(split_text),
                                page_start=block.page_number,
                                page_end=block.page_number,
                                section_path=current_section,
                                heading=current_heading,
                                source_offsets={"page_start": block.page_number, "char_length": len(split_text)},
                            )
                        )
                        chunk_idx += 1
                continue

            # If adding this block exceeds target chunk size, flush current buffer
            if current_len + len(text) > self.target_chunk_size and current_len >= self.min_chunk_size:
                flush_chunk()
                current_page_start = block.page_number
                current_page_end = block.page_number

            current_buffer.append(text)
            current_len += len(text)

        # Flush any remaining content in buffer
        flush_chunk()

        logger.info(
            "Chunked document '%s' into %d structure-aware chunks (avg %d chars/chunk).",
            doc.filename,
            len(chunks),
            sum(len(c.content) for c in chunks) // max(1, len(chunks)),
        )
        return chunks

    def _split_text_with_overlap(self, text: str) -> List[str]:
        """
        Splits long continuous text into chunks with bounded overlap, respecting sentences.
        """
        sentences = re.split(r"(?<=[.!?])\s+", text)
        result: List[str] = []
        current: List[str] = []
        current_len = 0

        for sentence in sentences:
            s_stripped = sentence.strip()
            if not s_stripped:
                continue

            if current_len + len(s_stripped) > self.target_chunk_size and current:
                chunk_str = " ".join(current).strip()
                result.append(chunk_str)

                # Overlap: keep the last sentence or two if within overlap limit
                overlap_buffer: List[str] = []
                overlap_len = 0
                for prev in reversed(current):
                    if overlap_len + len(prev) <= self.chunk_overlap:
                        overlap_buffer.insert(0, prev)
                        overlap_len += len(prev)
                    else:
                        break
                current = overlap_buffer
                current_len = overlap_len

            current.append(s_stripped)
            current_len += len(s_stripped)

        if current:
            chunk_str = " ".join(current).strip()
            if not result or chunk_str != result[-1]:
                result.append(chunk_str)

        return result
