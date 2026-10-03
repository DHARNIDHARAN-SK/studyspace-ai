import uuid
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from app.db.models import Document, DocumentChunk, Profile, Project, Workspace
from app.db.repository import Repository
from app.db.session import get_session_factory
from app.rag.embeddings.base import DimensionMismatchError, EmbeddingError
from app.rag.embeddings.ollama_provider import OllamaEmbeddingProvider
from app.rag.embeddings.service import ChunkEmbeddingService


@pytest.mark.asyncio
async def test_embedding_provider_dimension_validation():
    provider = OllamaEmbeddingProvider(dimension=768)

    # Valid dimension should pass
    valid_vec = [0.1] * 768
    provider.validate_dimension(valid_vec)

    # Invalid dimension should raise DimensionMismatchError
    invalid_vec = [0.1] * 512
    with pytest.raises(DimensionMismatchError) as exc_info:
        provider.validate_dimension(invalid_vec)
    assert exc_info.value.code == "EMBEDDING_DIMENSION_MISMATCH"
    assert exc_info.value.details["expected"] == 768
    assert exc_info.value.details["received"] == 512


@pytest.mark.asyncio
async def test_ollama_embedding_provider_single_and_batch():
    provider = OllamaEmbeddingProvider(dimension=768)

    # Mock Ollama /api/embed response
    mock_embeddings = [[0.05] * 768, [0.08] * 768]
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_resp.json = lambda: {"embeddings": mock_embeddings}
        mock_post.return_value = mock_resp

        # Test single text embedding
        emb = await provider.embed_text("Cloud Computing Basics")
        assert len(emb) == 768
        assert emb[0] == 0.05

        # Test batch embedding
        batch_embs = await provider.embed_batch(["Text 1", "Text 2"], batch_size=2)
        assert len(batch_embs) == 2
        assert len(batch_embs[0]) == 768
        assert len(batch_embs[1]) == 768


@pytest.mark.asyncio
async def test_chunk_embedding_service_persistence_and_idempotency():
    """Verifies that ChunkEmbeddingService writes embeddings to DB and skips on re-run."""
    session_factory = get_session_factory()
    user_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    from sqlalchemy import text
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_id, "email": f"embed-{user_id}@studyspace.ai"},
            )
            profile = Profile(id=user_id, display_name="Embed Student")
            session.add(profile)
            ws = Workspace(id=ws_id, owner_user_id=user_id, name="Embed Workspace")
            session.add(ws)
            proj = Project(id=proj_id, workspace_id=ws_id, name="Embed Project")
            session.add(proj)

            doc = Document(
                id=doc_id,
                workspace_id=ws_id,
                project_id=proj_id,
                uploaded_by_user_id=user_id,
                original_filename="notes.txt",
                storage_path="path/to/notes.txt",
                mime_type="text/plain",
                extension=".txt",
                byte_size=1024,
                ingestion_status="chunking",
            )
            session.add(doc)

            # Insert 3 unembedded chunks
            for i in range(3):
                chunk = DocumentChunk(
                    workspace_id=ws_id,
                    project_id=proj_id,
                    document_id=doc_id,
                    chunk_index=i,
                    content=f"This is sample content for chunk {i} about cloud models.",
                    page_start=i + 1,
                    page_end=i + 1,
                    embedding=None,
                )
                session.add(chunk)

    # Mock provider returning 768-dim vectors
    mock_provider = AsyncMock()
    mock_provider.dimension = 768
    mock_provider.provider_name = "ollama"
    mock_provider.model_id = "nomic-embed-text:latest"
    mock_provider.validate_dimension = lambda vec: None
    mock_provider.embed_batch = AsyncMock(return_value=[[0.02 * (i + 1)] * 768 for i in range(3)])

    service = ChunkEmbeddingService(provider=mock_provider)

    # Pass 1: embed chunks
    embedded_count = await service.embed_document_chunks(document_id=doc_id)
    assert embedded_count == 3
    mock_provider.embed_batch.assert_called_once()

    # Verify embeddings are persisted in DB
    async with session_factory() as session:
        res = await session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index.asc())
        )
        chunks = res.scalars().all()
        assert len(chunks) == 3
        for idx, chunk in enumerate(chunks):
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 768
            assert chunk.embedding_provider == "ollama"
            assert chunk.embedding_model_id == "nomic-embed-text:latest"

    # Pass 2: IDEMPOTENCY — re-running should detect chunks already embedded and skip without model call
    mock_provider.embed_batch.reset_mock()
    re_count = await service.embed_document_chunks(document_id=doc_id, force_reembed=False)
    assert re_count == 0
    mock_provider.embed_batch.assert_not_called()

    # Cleanup
    async with session_factory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": user_id})
