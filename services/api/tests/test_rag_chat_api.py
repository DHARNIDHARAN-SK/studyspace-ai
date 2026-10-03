import uuid
import pytest
from httpx import ASGITransport, AsyncClient
import jwt
from sqlalchemy import text
from unittest.mock import AsyncMock, patch

from app.core.auth import DEV_TEST_JWT_SECRET
from app.db.models import Conversation, Message, MessageCitation, Profile, Project, Workspace
from app.db.repository import Repository
from app.db.session import get_session_factory
from app.main import app
from app.rag.context.models import CitationSource
from app.rag.pipeline import BaselineRAGResult
from app.rag.retrieval.models import RetrievedChunk


def generate_test_token(user_id: str, email: str = "student@studyspace.ai") -> str:
    return jwt.encode(
        {"sub": user_id, "email": email, "aud": "authenticated", "role": "authenticated"},
        DEV_TEST_JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture
async def chat_test_env():
    session_factory = get_session_factory()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    Repository.upsert_profile(user_id=str(user_a), display_name="Chat Student A")
    Repository.upsert_profile(user_id=str(user_b), display_name="Chat Student B")
    ws_a_dict = Repository.get_or_create_workspace(user_id=str(user_a), default_name="Chat Workspace A")
    ws_b_dict = Repository.get_or_create_workspace(user_id=str(user_b), default_name="Chat Workspace B")
    ws_a = uuid.UUID(ws_a_dict["id"])
    ws_b = uuid.UUID(ws_b_dict["id"])
    proj_a = uuid.uuid4()
    proj_b = uuid.uuid4()

    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_a, "email": f"chata-{user_a}@studyspace.ai"},
            )
            await session.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_b, "email": f"chatb-{user_b}@studyspace.ai"},
            )
            session.add(Profile(id=user_a, display_name="Chat Student A"))
            session.add(Profile(id=user_b, display_name="Chat Student B"))
            session.add(Workspace(id=ws_a, owner_user_id=user_a, name="Chat Workspace A"))
            session.add(Workspace(id=ws_b, owner_user_id=user_b, name="Chat Workspace B"))
            session.add(Project(id=proj_a, workspace_id=ws_a, name="Distributed Systems"))
            session.add(Project(id=proj_b, workspace_id=ws_b, name="Operating Systems"))

    yield {
        "user_a": user_a, "ws_a": ws_a, "proj_a": proj_a,
        "user_b": user_b, "ws_b": ws_b, "proj_b": proj_b,
    }

    async with session_factory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM auth.users WHERE id IN (:id1, :id2)"), {"id1": user_a, "id2": user_b})


@pytest.mark.asyncio
async def test_chat_api_end_to_end_and_authorization(chat_test_env):
    env = chat_test_env
    token_a = generate_test_token(str(env["user_a"]))
    token_b = generate_test_token(str(env["user_b"]))

    mock_rag_result = BaselineRAGResult(
        query="What is distributed shared memory?",
        answer="Distributed shared memory allows multiple nodes to access a shared address space [OS_Notes.pdf, p. 14].",
        citations=[
            CitationSource(
                document_id=uuid.uuid4(),
                document_filename="OS_Notes.pdf",
                chunk_id=uuid.uuid4(),
                page_start=14,
                page_end=15,
                slide_number=None,
                section_path="Chapter 3: Memory Models",
                similarity_score=0.91,
                citation_label="[OS_Notes.pdf, pp. 14-15]",
                snippet="Distributed shared memory allows multiple nodes to access a shared address space.",
            )
        ],
        retrieved_chunks=[],
        llm_model="phi4-mini:latest",
        embedding_model="nomic-embed-text:latest",
        provider="ollama",
        total_latency_ms=840,
        retrieval_latency_ms=45,
        generation_latency_ms=795,
        token_usage={"prompt_tokens": 120, "completion_tokens": 30},
    )

    with patch("app.services.chat_service.BaselineRAGPipeline.execute", AsyncMock(return_value=mock_rag_result)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. User A successfully submits query to User A's project
            resp = await client.post(
                f"/api/v1/projects/{env['proj_a']}/chat",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"query": "What is distributed shared memory?", "top_k": 5},
            )
            assert resp.status_code == 200
            data = resp.json()

            conv_id = data["conversation_id"]
            msg = data["message"]
            metrics = data["metrics"]

            assert msg["role"] == "assistant"
            assert "Distributed shared memory" in msg["content"]
            assert len(msg["citations"]) == 1
            assert msg["citations"][0]["document_title"] == "OS_Notes.pdf"
            assert msg["citations"][0]["page_start"] == 14
            assert msg["latency_ms"] == 840
            assert msg["model"] == "phi4-mini:latest"
            assert metrics["model"] == "phi4-mini:latest"
            assert metrics["embedding_model"] == "nomic-embed-text:latest"

            # 2. List conversations
            list_resp = await client.get(
                f"/api/v1/projects/{env['proj_a']}/conversations",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert list_resp.status_code == 200
            conv_data = list_resp.json()
            assert conv_data["total"] >= 1
            assert any(c["id"] == conv_id for c in conv_data["conversations"])

            # 3. Get conversation message history
            history_resp = await client.get(
                f"/api/v1/projects/{env['proj_a']}/conversations/{conv_id}/messages",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert history_resp.status_code == 200
            history_data = history_resp.json()
            assert len(history_data["messages"]) == 2  # 1 user + 1 assistant
            assert history_data["messages"][0]["role"] == "user"
            assert history_data["messages"][1]["role"] == "assistant"
            assert len(history_data["messages"][1]["citations"]) == 1

            # 4. NEGATIVE TEST — Tenant Authorization:
            # User B attempts to query User A's project -> MUST BE FORBIDDEN (403)
            cross_resp = await client.post(
                f"/api/v1/projects/{env['proj_a']}/chat",
                headers={"Authorization": f"Bearer {token_b}"},
                json={"query": "Attempting cross-tenant access"},
            )
            assert cross_resp.status_code in (403, 404)
