import uuid
import pytest
from sqlalchemy import text
from app.db.models import Document, DocumentChunk, Profile, Project, Workspace
from app.db.session import check_db_health, get_engine, get_session_factory


@pytest.mark.asyncio
async def test_database_health_and_pgvector():
    health = await check_db_health()
    assert health["status"] == "healthy"
    assert health["pgvector_installed"] is True
    assert health["pgvector_version"] is not None
    assert health["table_count"] >= 19
    assert health["latency_ms"] is not None


@pytest.mark.asyncio
async def test_required_tables_exist():
    engine = get_engine()
    assert engine is not None

    expected_tables = {
        "profiles",
        "workspaces",
        "projects",
        "documents",
        "document_chunks",
        "conversations",
        "messages",
        "message_citations",
        "revision_items",
        "revision_item_links",
        "quizzes",
        "quiz_questions",
        "quiz_attempts",
        "quiz_responses",
        "study_guides",
        "exports",
        "api_keys",
        "usage_events",
        "ingestion_jobs",
    }

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        existing_tables = {row[0] for row in result.fetchall()}

        missing_tables = expected_tables - existing_tables
        assert not missing_tables, f"Missing tables in public schema: {missing_tables}"


@pytest.mark.asyncio
async def test_hnsw_vector_index_exists():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'document_chunks'")
        )
        indexes = {row[0]: row[1] for row in result.fetchall()}

        assert "idx_chunks_embedding_hnsw" in indexes
        assert "hnsw" in indexes["idx_chunks_embedding_hnsw"].lower()
        assert "vector_cosine_ops" in indexes["idx_chunks_embedding_hnsw"].lower()


@pytest.mark.asyncio
async def test_full_text_search_trigger_exists():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT trigger_name FROM information_schema.triggers WHERE event_object_table = 'document_chunks'")
        )
        triggers = {row[0] for row in result.fetchall()}
        assert "trg_document_chunks_search_vector" in triggers


@pytest.mark.asyncio
async def test_sqlalchemy_orm_and_cascading_deletion():
    session_factory = get_session_factory()
    assert session_factory is not None

    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()
    document_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    # Create dummy 768-dim vector
    dummy_embedding = [0.01] * 768

    async with session_factory() as session:
        # 0. Provision auth.users record (satisfying foreign key constraint)
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": user_id, "email": f"student-{user_id}@studyspace.ai"},
        )

        # 1. Create Profile
        profile = Profile(id=user_id, display_name="Test Student")
        session.add(profile)

        # 2. Create Workspace
        ws = Workspace(id=workspace_id, owner_user_id=user_id, name="Test CS Workspace")
        session.add(ws)

        # 3. Create Project
        proj = Project(
            id=project_id,
            workspace_id=workspace_id,
            name="Quantum Computing 101",
            subject="Computer Science",
        )
        session.add(proj)

        # 4. Create Document
        doc = Document(
            id=document_id,
            workspace_id=workspace_id,
            project_id=project_id,
            uploaded_by_user_id=user_id,
            original_filename="intro.pdf",
            storage_path=f"workspaces/{workspace_id}/projects/{project_id}/documents/{document_id}/intro.pdf",
            mime_type="application/pdf",
            extension=".pdf",
            byte_size=1024,
            checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ingestion_status="indexed",
        )
        session.add(doc)

        # 5. Create DocumentChunk with 768-dim embedding
        chunk = DocumentChunk(
            id=chunk_id,
            workspace_id=workspace_id,
            project_id=project_id,
            document_id=document_id,
            chunk_index=0,
            content="Quantum superposition is a fundamental principle of quantum mechanics.",
            content_hash="mock_hash_001",
            embedding=dummy_embedding,
            embedding_provider="ollama",
            embedding_model_id="nomic-embed-text",
            embedding_model_version="v1.5",
        )
        session.add(chunk)

        await session.commit()

    # Verify retrieval and trigger generation of search_vector
    async with session_factory() as session:
        fetched_chunk = await session.get(DocumentChunk, chunk_id)
        assert fetched_chunk is not None
        assert fetched_chunk.content == "Quantum superposition is a fundamental principle of quantum mechanics."
        assert fetched_chunk.embedding is not None
        assert len(fetched_chunk.embedding) == 768
        assert fetched_chunk.search_vector is not None

        # Verify cascading deletion by deleting the Profile
        fetched_profile = await session.get(Profile, user_id)
        assert fetched_profile is not None
        await session.delete(fetched_profile)
        await session.commit()

    # Verify everything downstream was cascade deleted
    async with session_factory() as session:
        assert await session.get(Profile, user_id) is None
        assert await session.get(Workspace, workspace_id) is None
        assert await session.get(Project, project_id) is None
        assert await session.get(Document, document_id) is None
        assert await session.get(DocumentChunk, chunk_id) is None


@pytest.mark.asyncio
async def test_transaction_rollback():
    session_factory = get_session_factory()
    user_id = uuid.uuid4()

    async with session_factory() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": user_id, "email": f"rollback-{user_id}@studyspace.ai"},
        )
        profile = Profile(id=user_id, display_name="Rollback User")
        session.add(profile)
        # Explicit rollback without commit
        await session.rollback()

    async with session_factory() as session:
        fetched = await session.get(Profile, user_id)
        assert fetched is None
