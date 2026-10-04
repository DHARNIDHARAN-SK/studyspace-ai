import io
import re
from typing import List, Optional
import pypdf

from app.core.errors import AppError
from app.core.logging import logger
from app.rag.parsing.base import BaseParser, ParsedBlock, ParsedDocument


class PDFParsingError(AppError):
    def __init__(self, message: str, code: str = "PDF_PARSING_FAILED", status_code: int = 400):
        super().__init__(message=message, code=code, status_code=status_code)


def _ocr_page_worker(img_bytes_list: List[bytes], lang: str = "en") -> str:
    """Worker function executed in ThreadPoolExecutor to run WinRT OCR safely outside main event loop."""
    import winocr
    from PIL import Image

    extracted: List[str] = []
    for raw in img_bytes_list:
        try:
            img = Image.open(io.BytesIO(raw))
            res = winocr.recognize_pil_sync(img, lang=lang)
            txt = res.get("text", "").strip()
            if txt:
                extracted.append(txt)
        except Exception:
            continue
    return "\n\n".join(extracted)


class PDFParser(BaseParser):
    """
    Production-ready PDF parser using pypdf.
    Designed to safely process documents up to 500 pages via streaming/page-by-page extraction.
    Preserves exact 1-indexed page boundaries, page count, and extracts structural headings.
    """

    @property
    def parser_name(self) -> str:
        return "pypdf"

    @property
    def parser_version(self) -> str:
        return getattr(pypdf, "__version__", "5.0.0")

    def _is_probable_heading(self, line: str) -> bool:
        """Heuristic check for section headings in academic PDFs."""
        stripped = line.strip()
        if not stripped or len(stripped) > 90:
            return False

        # Match numbered headings: "1. Introduction", "Chapter 2", "1.1 Architecture"
        if re.match(r"^(chapter\s+\d+|unit\s+\d+|module\s+\d+|\d+(\.\d+)*\s+[A-Z])", stripped, re.IGNORECASE):
            return True

        # Match uppercase or title case short phrases without ending punctuation
        if stripped.isupper() and len(stripped) > 3 and not stripped.endswith((".", ",", ";", ":")):
            return True

        return False

    def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        except Exception as exc:
            logger.error("Failed to read PDF file '%s': %s", filename, exc)
            raise PDFParsingError(f"Corrupted or invalid PDF document: {filename}")

        if reader.is_encrypted:
            try:
                # Attempt empty password decryption
                reader.decrypt("")
            except Exception:
                raise PDFParsingError(
                    f"PDF document is password protected: {filename}",
                    code="PDF_ENCRYPTED",
                    status_code=422,
                )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise PDFParsingError(f"PDF contains 0 pages: {filename}", code="EMPTY_DOCUMENT")

        blocks: List[ParsedBlock] = []
        total_extracted_chars = 0
        current_heading: Optional[str] = None
        section_path: Optional[str] = None

        for page_idx, page in enumerate(reader.pages):
            page_number = page_idx + 1  # 1-indexed for academic citation standard
            try:
                page_text = page.extract_text() or ""
            except Exception as page_exc:
                logger.warning("Error extracting text from page %d in '%s': %s", page_number, filename, page_exc)
                page_text = ""

            page_chars = len(page_text.strip())
            total_extracted_chars += page_chars

            if not page_text.strip():
                continue

            # Split page text into candidate paragraphs/lines
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            paragraph_buffer: List[str] = []

            for line in lines:
                if self._is_probable_heading(line):
                    # Flush accumulated paragraph before recording new heading
                    if paragraph_buffer:
                        p_content = " ".join(paragraph_buffer).strip()
                        if p_content:
                            blocks.append(
                                ParsedBlock(
                                    content=p_content,
                                    block_type="paragraph",
                                    page_number=page_number,
                                    heading=current_heading,
                                    section_path=section_path,
                                )
                            )
                        paragraph_buffer = []

                    current_heading = line
                    section_path = line
                    blocks.append(
                        ParsedBlock(
                            content=line,
                            block_type="heading",
                            page_number=page_number,
                            heading=current_heading,
                            section_path=section_path,
                        )
                    )
                else:
                    paragraph_buffer.append(line)

            # Flush any remaining paragraph on this page
            if paragraph_buffer:
                p_content = " ".join(paragraph_buffer).strip()
                if p_content:
                    blocks.append(
                        ParsedBlock(
                            content=p_content,
                            block_type="paragraph",
                            page_number=page_number,
                            heading=current_heading,
                            section_path=section_path,
                        )
                    )

        # Scanned document detection: if average text per page is extremely low (< 20 chars)
        is_scanned = False
        if total_pages > 0 and (total_extracted_chars / total_pages) < 20:
            is_scanned = True
            logger.info("PDF '%s' flagged as scanned or image-only (%d total chars over %d pages).", filename, total_extracted_chars, total_pages)

            # Attempt OCR recovery if no text blocks could be extracted
            if not blocks:
                try:
                    import concurrent.futures
                    logger.info("Initiating native multi-threaded OCR for scanned PDF '%s' (%d pages)...", filename, total_pages)

                    page_images = []
                    for page in reader.pages:
                        imgs = [img_obj.data for img_obj in page.images if hasattr(img_obj, "data")]
                        page_images.append(imgs)

                    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                        page_texts = list(executor.map(lambda imgs: _ocr_page_worker(imgs, "en"), page_images))

                    for page_idx, full_page_text in enumerate(page_texts):
                        page_number = page_idx + 1
                        if not full_page_text or not full_page_text.strip():
                            continue

                        total_extracted_chars += len(full_page_text)
                        lines = [l.strip() for l in full_page_text.splitlines() if l.strip()]
                        paragraph_buffer: List[str] = []
                        for line in lines:
                            if self._is_probable_heading(line):
                                if paragraph_buffer:
                                    p_content = " ".join(paragraph_buffer).strip()
                                    if p_content:
                                        blocks.append(
                                            ParsedBlock(
                                                content=p_content,
                                                block_type="paragraph",
                                                page_number=page_number,
                                                heading=current_heading,
                                                section_path=section_path,
                                            )
                                        )
                                    paragraph_buffer = []
                                current_heading = line
                                section_path = line
                                blocks.append(
                                    ParsedBlock(
                                        content=line,
                                        block_type="heading",
                                        page_number=page_number,
                                        heading=current_heading,
                                        section_path=section_path,
                                    )
                                )
                            else:
                                paragraph_buffer.append(line)
                        if paragraph_buffer:
                            p_content = " ".join(paragraph_buffer).strip()
                            if p_content:
                                blocks.append(
                                    ParsedBlock(
                                        content=p_content,
                                        block_type="paragraph",
                                        page_number=page_number,
                                        heading=current_heading,
                                        section_path=section_path,
                                    )
                                )
                    logger.info("OCR completed for '%s': extracted %d blocks across %d pages", filename, len(blocks), total_pages)
                except ImportError:
                    logger.info("OCR module not installed; skipping OCR for '%s'.", filename)
                except Exception as ocr_exc:
                    logger.warning("OCR processing failed for '%s': %s", filename, ocr_exc)

        # Metadata extraction
        metadata = {}
        if reader.metadata:
            for k, v in reader.metadata.items():
                if v and isinstance(v, (str, int, float, bool)):
                    clean_k = k.lstrip("/").lower()
                    metadata[clean_k] = str(v)

        return ParsedDocument(
            filename=filename,
            extension=".pdf",
            page_count=total_pages,
            blocks=blocks,
            is_scanned=is_scanned,
            metadata=metadata,
        )
