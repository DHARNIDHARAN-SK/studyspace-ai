import os
from pathlib import Path
import time
import uuid
import pytest
from sqlalchemy import select, func, text

from app.db.models import Document, DocumentChunk, IngestionJob, Profile, Project, Workspace
from app.db.repository import Repository
from app.db.session import get_session_factory
from app.rag.ingestion.pipeline import run_document_ingestion
from app.services.storage import LocalStorageProvider, DOCUMENTS_BUCKET, build_document_storage_path, calculate_sha256

REAL_PDF_PATH = Path(r"D:\RAG_DATA_TESTING\DECAP470_CLOUD_COMPUTING.pdf")


@pytest.mark.asyncio
async def test_real_cloud_computing_pdf_controlled_ingestion():
    """
    Controlled Phase 5 ingestion verification using the designated real test document:
    D:\\RAG_DATA_TESTING\\DECAP470_CLOUD_COMPUTING.pdf
    Strictly verifies:
      - Non-destructive read (original file preserved)
      - Document and Job creation
      - Structure extraction & page metadata preservation
      - Structure-aware chunking without duplicate chunks
      - Document status becomes 'indexed'
      - Zero embeddings or RAG generation
    """
    assert REAL_PDF_PATH.exists(), f"Designated test PDF not found at {REAL_PDF_PATH}"
    initial_mtime = REAL_PDF_PATH.stat().st_mtime
    initial_size = REAL_PDF_PATH.stat().st_size

    # 1. Read bytes without modifying original file
    with open(REAL_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    assert len(pdf_bytes) == initial_size
    computed_checksum = calculate_sha256(pdf_bytes)

    # 2. Setup tenant hierarchy in PostgreSQL
    session_factory = get_session_factory()
    user_id = uuid.uuid4()
    Repository.upsert_profile(user_id=str(user_id), display_name="Cloud Student")
    ws_dict = Repository.get_or_create_workspace(user_id=str(user_id), default_name="Cloud Computing Workspace")
    ws_id = uuid.UUID(ws_dict["id"])
    proj_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_id, "email": f"cloud-{user_id}@studyspace.ai"},
            )
            profile = Profile(id=user_id, display_name="Cloud Student")
            session.add(profile)
            ws = Workspace(id=ws_id, owner_user_id=user_id, name="Cloud Computing Workspace")
            session.add(ws)
            proj = Project(
                id=proj_id,
                workspace_id=ws_id,
                name="Cloud Computing Course",
                subject="DECAP470",
            )
            session.add(proj)

    # 3. Store in private storage foundation
    storage_provider = LocalStorageProvider(base_dir=Path("uploads"))
    safe_filename = "DECAP470_CLOUD_COMPUTING.pdf"
    storage_path = build_document_storage_path(ws_id, proj_id, doc_id, safe_filename)

    await storage_provider.put_object(
        bucket=DOCUMENTS_BUCKET,
        path=storage_path,
        data=pdf_bytes,
        content_type="application/pdf",
    )

    # 4. Insert initial queued Document and IngestionJob
    async with session_factory() as session:
        async with session.begin():
            document = Document(
                id=doc_id,
                workspace_id=ws_id,
                project_id=proj_id,
                uploaded_by_user_id=user_id,
                original_filename=safe_filename,
                storage_path=storage_path,
                mime_type="application/pdf",
                extension=".pdf",
                byte_size=len(pdf_bytes),
                checksum=computed_checksum,
                document_version=1,
                ingestion_status="queued",
            )
            session.add(document)

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

    # 5. Execute Ingestion Pipeline and measure performance
    start_time = time.time()
    result = await run_document_ingestion(
        document_id=doc_id,
        workspace_id=ws_id,
        project_id=proj_id,
        job_id=job_id,
        storage_provider=storage_provider,
    )
    duration = time.time() - start_time

    # 6. Verify pipeline result
    assert result["status"] == "indexed"
    assert result["parser_name"] == "pypdf"
    assert result["page_count"] is not None and result["page_count"] > 0
    assert result["chunk_count"] > 0

    print(f"\n[Real Document Ingestion Result]")
    print(f"File: {safe_filename} ({len(pdf_bytes):,} bytes)")
    print(f"Total Pages: {result['page_count']}")
    print(f"Total Chunks: {result['chunk_count']}")
    print(f"Processing Duration: {duration:.2f} seconds")

    # 7. Verify Database persistence
    async with session_factory() as session:
        # Document record
        doc = await session.get(Document, doc_id)
        assert doc is not None
        assert doc.ingestion_status == "indexed"
        assert doc.page_count == result["page_count"]
        assert doc.indexed_at is not None
        assert doc.checksum == computed_checksum

        # Job record
        job = await session.get(IngestionJob, job_id)
        assert job is not None
        assert job.status == "completed"
        assert job.stage == "indexed"
        assert job.progress_metadata.get("chunk_count") == result["chunk_count"]

        # Chunks verification
        chunk_count_res = await session.execute(
            select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc_id)
        )
        assert chunk_count_res.scalar() == result["chunk_count"]

        # Verify page numbers are preserved across chunks
        chunks_sample = (
            await session.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == doc_id).limit(20)
            )
        ).scalars().all()

        for chunk in chunks_sample:
            assert chunk.page_start is not None
            assert chunk.page_start >= 1
            assert chunk.page_start <= result["page_count"]
            assert chunk.content_hash is not None
            assert chunk.token_count > 0
            assert chunk.embedding is None  # EMBEDDINGS STRICTLY NOT GENERATED IN PHASE 5

    # 8. Verify Idempotency: Re-running ingestion must NOT duplicate chunks
    re_result = await run_document_ingestion(
        document_id=doc_id,
        workspace_id=ws_id,
        project_id=proj_id,
        job_id=job_id,
        storage_provider=storage_provider,
    )
    assert re_result["status"] == "indexed"

    async with session_factory() as session:
        chunk_count_res2 = await session.execute(
            select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc_id)
        )
        assert chunk_count_res2.scalar() == result["chunk_count"], "Chunks were duplicated upon re-run!"

    # 9. Verify original file was completely unharmed
    assert REAL_PDF_PATH.stat().st_mtime == initial_mtime
    assert REAL_PDF_PATH.stat().st_size == initial_size

    # Cleanup test artifacts
    async with session_factory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": user_id})
    await storage_provider.delete_object(DOCUMENTS_BUCKET, storage_path)
