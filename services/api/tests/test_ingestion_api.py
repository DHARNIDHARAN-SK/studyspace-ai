import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
import jwt
from sqlalchemy import select, func

from app.core.auth import DEV_TEST_JWT_SECRET
from app.db.models import Document, DocumentChunk, IngestionJob, Profile, Project, Workspace
from app.db.session import get_session_factory
from app.main import app
from app.rag.ingestion.pipeline import run_document_ingestion
from app.services.storage import LocalStorageProvider, DOCUMENTS_BUCKET
from tests.test_ingestion_parsers import create_sample_docx_bytes, create_sample_pdf_bytes


def generate_test_token(user_id: str, email: str = "student@studyspace.ai") -> str:
    """Generates valid JWT for testing."""
    return jwt.encode(
        {"sub": user_id, "email": email, "aud": "authenticated", "role": "authenticated"},
        DEV_TEST_JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture
async def setup_test_hierarchy():
    """Sets up a clean workspace and project in PostgreSQL for ingestion tests."""
    from sqlalchemy import text
    from app.db.repository import Repository
    session_factory = get_session_factory()
    user_id = uuid.uuid4()
    
    # Provision via Repository first so get_current_user aligns with PostgreSQL
    Repository.upsert_profile(user_id=str(user_id), display_name="Test Student")
    ws_dict = Repository.get_or_create_workspace(user_id=str(user_id), default_name="Test CS Workspace")
    ws_id = uuid.UUID(ws_dict["id"])
    proj_id = uuid.uuid4()

    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_id, "email": f"test-{user_id}@studyspace.ai"},
            )
            profile = Profile(id=user_id, display_name="Test Student")
            session.add(profile)
            ws = Workspace(id=ws_id, owner_user_id=user_id, name="Test CS Workspace")
            session.add(ws)
            proj = Project(id=proj_id, workspace_id=ws_id, name="Cloud Computing", subject="CS 452")
            session.add(proj)

    yield {"user_id": user_id, "workspace_id": ws_id, "project_id": proj_id}

    # Cleanup
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM auth.users WHERE id = :id"),
                {"id": user_id},
            )


@pytest.mark.asyncio
async def test_upload_document_endpoint_pdf(setup_test_hierarchy):
    env = setup_test_hierarchy
    token = generate_test_token(str(env["user_id"]))
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("lecture1.pdf", pdf_bytes, "application/pdf")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/projects/{env['project_id']}/documents",
            headers=headers,
            files=files,
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["job_id"] is not None
    doc = data["document"]
    assert doc["original_filename"] == "lecture1.pdf"
    assert doc["extension"] == ".pdf"
    assert doc["byte_size"] == len(pdf_bytes)
    assert doc["project_id"] == str(env["project_id"])


@pytest.mark.asyncio
async def test_upload_unsupported_file_rejected(setup_test_hierarchy):
    env = setup_test_hierarchy
    token = generate_test_token(str(env["user_id"]))
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("malicious.exe", b"MZ\x90\x00binary", "application/x-msdownload")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/projects/{env['project_id']}/documents",
            headers=headers,
            files=files,
        )

    assert resp.status_code == 415
    data = resp.json()
    assert data["error"]["code"] == "UNSUPPORTED_FILE_FORMAT"


@pytest.mark.asyncio
async def test_list_and_get_documents_endpoint(setup_test_hierarchy):
    env = setup_test_hierarchy
    token = generate_test_token(str(env["user_id"]))
    headers = {"Authorization": f"Bearer {token}"}

    docx_bytes = create_sample_docx_bytes()
    files = {"file": ("syllabus.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Upload
        up_resp = await client.post(
            f"/api/v1/projects/{env['project_id']}/documents",
            headers=headers,
            files=files,
        )
        assert up_resp.status_code == 202
        doc_id = up_resp.json()["document"]["id"]

        # 2. List
        list_resp = await client.get(
            f"/api/v1/projects/{env['project_id']}/documents",
            headers=headers,
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        assert any(d["id"] == doc_id for d in list_data["documents"])

        # 3. Get single
        get_resp = await client.get(
            f"/api/v1/projects/{env['project_id']}/documents/{doc_id}",
            headers=headers,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_cross_tenant_document_isolation(setup_test_hierarchy):
    env = setup_test_hierarchy
    token_a = generate_test_token(str(env["user_id"]))
    
    # Another user/tenant
    other_user_id = uuid.uuid4()
    token_b = generate_test_token(str(other_user_id))

    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("private_notes.pdf", pdf_bytes, "application/pdf")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # User A uploads doc
        up_resp = await client.post(
            f"/api/v1/projects/{env['project_id']}/documents",
            headers={"Authorization": f"Bearer {token_a}"},
            files=files,
        )
        assert up_resp.status_code == 202
        doc_id = up_resp.json()["document"]["id"]

        # User B attempts to access User A's document -> 404 / 403 denied
        get_resp = await client.get(
            f"/api/v1/projects/{env['project_id']}/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert get_resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_end_to_end_ingestion_pipeline_and_idempotency(setup_test_hierarchy):
    env = setup_test_hierarchy
    token = generate_test_token(str(env["user_id"]))
    headers = {"Authorization": f"Bearer {token}"}

    docx_bytes = create_sample_docx_bytes()
    files = {"file": ("cloud_service_models.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        up_resp = await client.post(
            f"/api/v1/projects/{env['project_id']}/documents",
            headers=headers,
            files=files,
        )
        assert up_resp.status_code == 202
        data = up_resp.json()
        doc_id = data["document"]["id"]
        job_id = data["job_id"]

    # Execute pipeline directly to verify end-to-end processing & DB state
    result = await run_document_ingestion(
        document_id=doc_id,
        workspace_id=env["workspace_id"],
        project_id=env["project_id"],
        job_id=job_id,
    )

    assert result["status"] == "indexed"
    assert result["chunk_count"] > 0
    assert result["parser_name"] == "python-docx"

    # Verify DB records
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Check Document
        doc = await session.get(Document, uuid.UUID(doc_id))
        assert doc is not None
        assert doc.ingestion_status == "indexed"
        assert doc.indexed_at is not None
        assert doc.checksum is not None

        # Check Chunks count
        chunk_count_stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == uuid.UUID(doc_id))
        count_res = await session.execute(chunk_count_stmt)
        initial_chunk_count = count_res.scalar()
        assert initial_chunk_count == result["chunk_count"]

    # Re-run pipeline to verify IDEMPOTENCY (duplicate chunk prevention)
    re_result = await run_document_ingestion(
        document_id=doc_id,
        workspace_id=env["workspace_id"],
        project_id=env["project_id"],
        job_id=job_id,
    )
    assert re_result["status"] == "indexed"

    async with session_factory() as session:
        count_res2 = await session.execute(chunk_count_stmt)
        second_chunk_count = count_res2.scalar()
        # Chunks must NOT have doubled!
        assert second_chunk_count == initial_chunk_count


@pytest.mark.asyncio
async def test_retry_document_ingestion_endpoint(setup_test_hierarchy):
    env = setup_test_hierarchy
    token = generate_test_token(str(env["user_id"]))
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("retry_test.pdf", pdf_bytes, "application/pdf")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        up_resp = await client.post(
            f"/api/v1/projects/{env['project_id']}/documents",
            headers=headers,
            files=files,
        )
        assert up_resp.status_code == 202
        doc_id = up_resp.json()["document"]["id"]

        # Call retry endpoint
        retry_resp = await client.post(
            f"/api/v1/projects/{env['project_id']}/documents/{doc_id}/retry",
            headers=headers,
        )
        assert retry_resp.status_code == 200
        assert retry_resp.json()["ingestion_status"] == "queued"


@pytest.mark.asyncio
async def test_delete_document_endpoint(setup_test_hierarchy):
    env = setup_test_hierarchy
    token = generate_test_token(str(env["user_id"]))
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("to_delete.pdf", pdf_bytes, "application/pdf")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        up_resp = await client.post(
            f"/api/v1/projects/{env['project_id']}/documents",
            headers=headers,
            files=files,
        )
        doc_id = up_resp.json()["document"]["id"]

        # Delete
        del_resp = await client.delete(
            f"/api/v1/projects/{env['project_id']}/documents/{doc_id}",
            headers=headers,
        )
        assert del_resp.status_code == 204

        # Verify not returned in listing
        list_resp = await client.get(
            f"/api/v1/projects/{env['project_id']}/documents",
            headers=headers,
        )
        doc_ids = [d["id"] for d in list_resp.json()["documents"]]
        assert doc_id not in doc_ids
