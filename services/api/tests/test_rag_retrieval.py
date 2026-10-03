import uuid
import pytest
from unittest.mock import AsyncMock
from sqlalchemy import text

from app.db.models import Document, DocumentChunk, Profile, Project, Workspace
from app.db.session import get_session_factory
from app.rag.retrieval.vector_retriever import VectorRetriever


@pytest.mark.asyncio
async def test_vector_retrieval_and_tenant_isolation():
    """
    Verifies:
      1. Vector retrieval finds the most relevant chunk based on cosine similarity
      2. Top-K limits results properly
      3. Strict tenant isolation: Tenant B never retrieves Tenant A's chunks (negative test)
      4. Project filtering: Queries in Project 1 never return Project 2 chunks
    """
    session_factory = get_session_factory()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    ws_a_id = uuid.uuid4()
    ws_b_id = uuid.uuid4()
    proj_a1_id = uuid.uuid4()
    proj_a2_id = uuid.uuid4()
    proj_b_id = uuid.uuid4()
    doc_a1_id = uuid.uuid4()
    doc_a2_id = uuid.uuid4()
    doc_b_id = uuid.uuid4()

    # Create dummy 768d unit vectors
    # Vector 1: heavily weighted on dimension 0
    vec_cloud = [0.0] * 768
    vec_cloud[0] = 1.0

    # Vector 2: heavily weighted on dimension 1
    vec_security = [0.0] * 768
    vec_security[1] = 1.0

    # Vector 3: Tenant B vector
    vec_tenant_b = [0.0] * 768
    vec_tenant_b[0] = 1.0  # Identical direction to vec_cloud, but in Tenant B workspace!

    async with session_factory() as session:
        async with session.begin():
            # Setup Tenant A
            await session.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_a_id, "email": f"tenant-a-{user_a_id}@studyspace.ai"},
            )
            session.add(Profile(id=user_a_id, display_name="Student A"))
            session.add(Workspace(id=ws_a_id, owner_user_id=user_a_id, name="Workspace A"))
            session.add(Project(id=proj_a1_id, workspace_id=ws_a_id, name="Cloud Computing A1"))
            session.add(Project(id=proj_a2_id, workspace_id=ws_a_id, name="Algorithms A2"))

            session.add(Document(
                id=doc_a1_id, workspace_id=ws_a_id, project_id=proj_a1_id, uploaded_by_user_id=user_a_id,
                original_filename="cloud_lecture.pdf", storage_path="p1", mime_type="application/pdf",
                extension=".pdf", byte_size=1024, ingestion_status="indexed",
            ))
            session.add(Document(
                id=doc_a2_id, workspace_id=ws_a_id, project_id=proj_a2_id, uploaded_by_user_id=user_a_id,
                original_filename="algorithms.pdf", storage_path="p2", mime_type="application/pdf",
                extension=".pdf", byte_size=1024, ingestion_status="indexed",
            ))

            session.add(DocumentChunk(
                workspace_id=ws_a_id, project_id=proj_a1_id, document_id=doc_a1_id, chunk_index=0,
                content="Cloud computing delivers computing services over the internet.",
                page_start=5, page_end=5, embedding=vec_cloud,
            ))
            session.add(DocumentChunk(
                workspace_id=ws_a_id, project_id=proj_a1_id, document_id=doc_a1_id, chunk_index=1,
                content="Network security protocols ensure encrypted data transfer.",
                page_start=12, page_end=12, embedding=vec_security,
            ))
            session.add(DocumentChunk(
                workspace_id=ws_a_id, project_id=proj_a2_id, document_id=doc_a2_id, chunk_index=0,
                content="Sorting algorithms such as quicksort have O(n log n) average complexity.",
                page_start=1, page_end=1, embedding=vec_cloud,  # Same vector but in Project A2
            ))

            # Setup Tenant B (completely separate workspace)
            await session.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_b_id, "email": f"tenant-b-{user_b_id}@studyspace.ai"},
            )
            session.add(Profile(id=user_b_id, display_name="Student B"))
            session.add(Workspace(id=ws_b_id, owner_user_id=user_b_id, name="Workspace B"))
            session.add(Project(id=proj_b_id, workspace_id=ws_b_id, name="Private Project B"))
            session.add(Document(
                id=doc_b_id, workspace_id=ws_b_id, project_id=proj_b_id, uploaded_by_user_id=user_b_id,
                original_filename="confidential_b.pdf", storage_path="pb", mime_type="application/pdf",
                extension=".pdf", byte_size=1024, ingestion_status="indexed",
            ))
            session.add(DocumentChunk(
                workspace_id=ws_b_id, project_id=proj_b_id, document_id=doc_b_id, chunk_index=0,
                content="Tenant B confidential private research data.",
                page_start=1, page_end=1, embedding=vec_tenant_b,
            ))

    # Mock embedding provider: query for "cloud computing" returns query vector matching vec_cloud
    mock_provider = AsyncMock()
    mock_provider.dimension = 768
    mock_provider.validate_dimension = lambda vec: None
    mock_provider.embed_text = AsyncMock(return_value=vec_cloud)

    retriever = VectorRetriever(embedding_provider=mock_provider)

    # 1. Retrieve in Workspace A, Project A1
    results_a1 = await retriever.retrieve(
        query="What is cloud computing?",
        workspace_id=ws_a_id,
        project_id=proj_a1_id,
        top_k=5,
    )
    assert len(results_a1) == 2
    # The cloud chunk has cosine distance 0 => similarity 1.0 (highest rank)
    top_chunk = results_a1[0]
    assert "Cloud computing delivers" in top_chunk.content
    assert top_chunk.page_start == 5
    assert top_chunk.document_filename == "cloud_lecture.pdf"
    assert top_chunk.similarity_score > 0.99

    # The second chunk (security) is orthogonal => cosine distance 1.0 => similarity 0.0
    second_chunk = results_a1[1]
    assert "Network security" in second_chunk.content

    # 2. Project isolation: Project A1 query MUST NOT return Project A2 chunk even though vector matched
    for res in results_a1:
        assert res.project_id == proj_a1_id
        assert "Sorting algorithms" not in res.content

    # 3. NEGATIVE TEST — Cross-Tenant Isolation:
    # Query executed in Tenant B workspace MUST NEVER return Tenant A's chunks
    results_b = await retriever.retrieve(
        query="What is cloud computing?",
        workspace_id=ws_b_id,
        project_id=proj_b_id,
        top_k=5,
    )
    assert len(results_b) == 1
    assert results_b[0].workspace_id == ws_b_id
    assert results_b[0].document_filename == "confidential_b.pdf"
    assert "Tenant B confidential" in results_b[0].content
    for res in results_b:
        assert "Cloud computing delivers" not in res.content
        assert res.workspace_id != ws_a_id

    # 4. Top-K limit verification
    results_top1 = await retriever.retrieve(
        query="What is cloud computing?",
        workspace_id=ws_a_id,
        project_id=proj_a1_id,
        top_k=1,
    )
    assert len(results_top1) == 1

    # Cleanup
    async with session_factory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM auth.users WHERE id IN (:id1, :id2)"), {"id1": user_a_id, "id2": user_b_id})
