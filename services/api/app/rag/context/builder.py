from typing import List, Set
from app.core.config import settings
from app.rag.context.models import BuildContextResult, CitationSource
from app.rag.retrieval.models import RetrievedChunk


class ContextBuilder:
    """
    Constructs clean, bounded context blocks from retrieved chunks while preserving
    traceable provenance and preparing accurate source citation objects.
    """

    def __init__(self, max_context_chars: int = settings.RAG_MAX_CONTEXT_CHARS):
        self.max_context_chars = max_context_chars

    def build_context(
        self,
        chunks: List[RetrievedChunk],
        max_chars: int | None = None,
    ) -> BuildContextResult:
        """
        Assembles context string and citation list from retrieved chunks.
        Removes exact content duplicates and respects character boundaries.
        """
        max_chars = max_chars or self.max_context_chars

        if not chunks:
            return BuildContextResult(
                context_text="",
                citations=[],
                total_chars=0,
            )

        seen_contents: Set[str] = set()
        context_blocks: List[str] = []
        citations: List[CitationSource] = []
        current_chars = 0

        for chunk in chunks:
            norm_content = chunk.content.strip()
            if not norm_content or norm_content in seen_contents:
                continue

            seen_contents.add(norm_content)

            # Build readable citation label
            if chunk.page_start:
                if chunk.page_end and chunk.page_end != chunk.page_start:
                    loc_str = f"pp. {chunk.page_start}-{chunk.page_end}"
                else:
                    loc_str = f"p. {chunk.page_start}"
            elif chunk.slide_number:
                loc_str = f"Slide {chunk.slide_number}"
            else:
                loc_str = f"Chunk {chunk.chunk_index}"

            citation_label = f"[{chunk.document_filename}, {loc_str}]"

            # Create clean block header
            header_parts = [f"Source: {chunk.document_filename}", loc_str]
            if chunk.section_path:
                header_parts.append(chunk.section_path)
            elif chunk.heading:
                header_parts.append(chunk.heading)

            block_header = f"--- [{ ' | '.join(header_parts) }] ---"
            block_text = f"{block_header}\n{norm_content}\n"

            # Check capacity
            if current_chars + len(block_text) > max_chars and context_blocks:
                # Do not overflow context window
                break

            context_blocks.append(block_text)
            current_chars += len(block_text)

            # Snippet of first ~180 chars for citations
            snippet = norm_content[:200] + ("..." if len(norm_content) > 200 else "")

            citations.append(
                CitationSource(
                    document_id=chunk.document_id,
                    document_filename=chunk.document_filename,
                    chunk_id=chunk.chunk_id,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    slide_number=chunk.slide_number,
                    section_path=chunk.section_path,
                    similarity_score=chunk.similarity_score,
                    citation_label=citation_label,
                    snippet=snippet,
                )
            )

        assembled_context = "\n".join(context_blocks).strip()

        return BuildContextResult(
            context_text=assembled_context,
            citations=citations,
            total_chars=len(assembled_context),
        )
