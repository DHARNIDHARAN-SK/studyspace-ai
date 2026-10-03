import asyncio
import os
from pathlib import Path
import sys
import time
import uuid

# Ensure services/api is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services" / "api"))

from sqlalchemy import delete, select, text
from app.core.config import settings
from app.core.logging import logger
from app.db.models import Document, DocumentChunk, IngestionJob, Profile, Project, Workspace
from app.db.session import get_session_factory
from app.rag.embeddings.service import ChunkEmbeddingService
from app.rag.ingestion.pipeline import run_document_ingestion
from app.services.storage import LocalStorageProvider, DOCUMENTS_BUCKET, build_document_storage_path, calculate_sha256

REAL_PDF_PATH = Path(r"D:\RAG_DATA_TESTING\DECAP470_CLOUD_COMPUTING.pdf")
WS_ID = uuid.UUID("6869b194-56b0-47c9-bb2c-2d373e02706e")
PROJ_ID = uuid.UUID("a0583e36-c065-43eb-a020-35fb160f5580")
USER_ID = uuid.UUID("23e5f4e6-35f2-4992-ae23-1f7db4ea61de")


async def main():
    print(f"Checking test document at {REAL_PDF_PATH}...")
    if not REAL_PDF_PATH.exists():
        print(f"Error: {REAL_PDF_PATH} not found.")
        sys.exit(1)

    initial_mtime = REAL_PDF_PATH.stat().st_mtime
    initial_size = REAL_PDF_PATH.stat().st_size
    print(f"Found {REAL_PDF_PATH.name} ({initial_size:,} bytes)")

    with open(REAL_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    checksum = calculate_sha256(pdf_bytes)

    session_factory = get_session_factory()
    doc_id = uuid.UUID("dcbce759-728f-471f-9233-4f112546fa54")
    job_id = uuid.uuid4()
    storage_provider = LocalStorageProvider(base_dir=settings.UPLOAD_DIR)
    safe_filename = "DECAP470_CLOUD_COMPUTING.pdf"
    storage_path = build_document_storage_path(WS_ID, PROJ_ID, doc_id, safe_filename)

    # 1. Put into private storage
    print(f"Uploading to private storage: {storage_path}...")
    await storage_provider.put_object(
        bucket=DOCUMENTS_BUCKET,
        path=storage_path,
        data=pdf_bytes,
        content_type="application/pdf",
    )

    # 2. Update / Insert document record
    async with session_factory() as session:
        async with session.begin():
            doc = await session.get(Document, doc_id)
            if not doc:
                doc = Document(
                    id=doc_id,
                    workspace_id=WS_ID,
                    project_id=PROJ_ID,
                    uploaded_by_user_id=USER_ID,
                    original_filename=safe_filename,
                    storage_path=storage_path,
                    mime_type="application/pdf",
                    extension=".pdf",
                    byte_size=len(pdf_bytes),
                    checksum=checksum,
                    ingestion_status="queued",
                )
                session.add(doc)
            else:
                doc.storage_path = storage_path
                doc.checksum = checksum
                doc.byte_size = len(pdf_bytes)
                doc.ingestion_status = "queued"

            job = IngestionJob(
                id=job_id,
                document_id=doc_id,
                document_version=1,
                job_type="full_ingestion",
                status="queued",
                stage="queued",
                attempt_count=0,
            )
            session.add(job)

    # 3. Execute Phase 5 Ingestion Pipeline (Parsing + Chunking)
    print("Running document ingestion pipeline (parsing & chunking)...")
    t0 = time.time()
    result = await run_document_ingestion(
        document_id=doc_id,
        workspace_id=WS_ID,
        project_id=PROJ_ID,
        job_id=job_id,
        storage_provider=storage_provider,
        generate_embeddings=False,
    )
    t_ingest = time.time() - t0
    print(f"Ingestion complete: {result['chunk_count']} chunks from {result['page_count']} pages in {t_ingest:.2f}s")

    # 4. Execute Phase 6 Chunk Embedding Service (Batch embeddings with nomic-embed-text)
    print("Generating 768-dimensional embeddings via Ollama nomic-embed-text:latest...")
    embed_service = ChunkEmbeddingService()
    t1 = time.time()
    embedded_count = await embed_service.embed_document_chunks(
        document_id=doc_id,
        batch_size=32,
        force_reembed=True,
    )
    t_embed = time.time() - t1
    print(f"Embedding complete: {embedded_count} chunks embedded and saved in {t_embed:.2f}s (avg {embedded_count / t_embed:.1f} chunks/s)")

    # 5. Check original file intact
    assert REAL_PDF_PATH.stat().st_mtime == initial_mtime
    assert REAL_PDF_PATH.stat().st_size == initial_size
    print("Verification: original PDF file completely untouched!")

    # 6. Verify pgvector records in DB
    async with session_factory() as session:
        res = await session.execute(
            text("SELECT count(*), count(embedding) FROM document_chunks WHERE document_id = :id"),
            {"id": doc_id},
        )
        total, embedded = res.one()
        print(f"Database verification: {embedded}/{total} chunks have 768-dimensional embeddings stored in pgvector!")


if __name__ == "__main__":
    asyncio.run(main())
