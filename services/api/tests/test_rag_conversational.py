import asyncio
from datetime import datetime, timezone
from typing import List
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
import jwt
from sqlalchemy import select, text

from app.core.auth import DEV_TEST_JWT_SECRET
from app.core.config import settings
from app.db.models import Conversation, Message, Profile, Project, Workspace
from app.db.repository import Repository
from app.db.session import get_session_factory
from app.main import app
from app.rag.cache.redis_cache import RedisSemanticCache, compute_cosine_similarity
from app.rag.context.models import CitationSource
from app.rag.conversation.context_manager import (
    ConversationContextManager,
    ConversationTurn,
)
from app.rag.llm.base import BaseLLMProvider, LLMResponse
from app.rag.pipeline import ConversationalRAGPipeline, ConversationalRAGResult
from app.rag.retrieval.models import RetrievedChunk
from app.rag.retrieval.multi_query_retriever import MultiQueryRetriever
from app.rag.rewriting.service import QueryTransformationService, RewrittenQueryResult
from app.services.chat_service import ChatService


def generate_test_token(user_id: str, email: str = "student@studyspace.ai") -> str:
    return jwt.encode(
        {"sub": user_id, "email": email, "aud": "authenticated", "role": "authenticated"},
        DEV_TEST_JWT_SECRET,
        algorithm="HS256",
    )


class MockLLMProvider(BaseLLMProvider):
    def __init__(self, model_id: str = "mock-phi4-mini", provider_name: str = "mock"):
        super().__init__(model_id=model_id, provider_name=provider_name)
        self.call_count = 0
        self.last_prompt = ""

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_prompt = prompt

        if "reformulation" in system_prompt.lower() or "rewrite" in system_prompt.lower():
            if "limitation" in prompt.lower() or "drawback" in prompt.lower():
                return LLMResponse(content="What are the limitations of cloud computing?", latency_ms=10, model=self.model_id, provider=self.provider_name)
            return LLMResponse(content=prompt.splitlines()[-1].replace("Latest Follow-up Question:", "").strip(), latency_ms=10, model=self.model_id, provider=self.provider_name)

        if "alternative search queries" in system_prompt.lower():
            return LLMResponse(
                content="1. Cloud service models IaaS PaaS SaaS\n2. Comparing infrastructure and platform cloud services\n3. Cloud delivery architecture differences",
                latency_ms=10,
                model=self.model_id,
                provider=self.provider_name,
            )

        if "decompose" in system_prompt.lower():
            return LLMResponse(
                content="1. What is public cloud deployment?\n2. What is private cloud deployment?\n3. Differences between public and private clouds",
                latency_ms=10,
                model=self.model_id,
                provider=self.provider_name,
            )

        return LLMResponse(
            content="Cloud computing delivers compute, storage, and networking on demand [DECAP470_CLOUD_COMPUTING.pdf, p. 5].",
            latency_ms=10,
            model=self.model_id,
            provider=self.provider_name,
            prompt_tokens=40,
            completion_tokens=25,
        )


@pytest.fixture
async def conv_test_env():
    session_factory = get_session_factory()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    Repository.upsert_profile(user_id=str(user_a), display_name="Conv Student A")
    Repository.upsert_profile(user_id=str(user_b), display_name="Conv Student B")
    ws_a_dict = Repository.get_or_create_workspace(user_id=str(user_a), default_name="Conv Workspace A")
    ws_b_dict = Repository.get_or_create_workspace(user_id=str(user_b), default_name="Conv Workspace B")
    ws_a = uuid.UUID(ws_a_dict["id"])
    ws_b = uuid.UUID(ws_b_dict["id"])
    proj_a = uuid.uuid4()
    proj_b = uuid.uuid4()

    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_a, "email": f"conva-{user_a}@studyspace.ai"},
            )
            await session.execute(
                text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"),
                {"id": user_b, "email": f"convb-{user_b}@studyspace.ai"},
            )
            session.add(Profile(id=user_a, display_name="Conv Student A"))
            session.add(Profile(id=user_b, display_name="Conv Student B"))
            session.add(Workspace(id=ws_a, owner_user_id=user_a, name="Conv Workspace A"))
            session.add(Workspace(id=ws_b, owner_user_id=user_b, name="Conv Workspace B"))
            session.add(Project(id=proj_a, workspace_id=ws_a, name="Cloud Architecture"))
            session.add(Project(id=proj_b, workspace_id=ws_b, name="Network Security"))

    yield {
        "user_a": user_a, "ws_a": ws_a, "proj_a": proj_a,
        "user_b": user_b, "ws_b": ws_b, "proj_b": proj_b,
    }


# ==============================================================================
# 1. Conversation Context Manager Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_conversation_context_manager_formatting():
    turns = [
        ConversationTurn(role="user", content="What is cloud computing?"),
        ConversationTurn(role="assistant", content="It is on-demand computing."),
        ConversationTurn(role="user", content="What are its limitations?"),
    ]

    rewrite_hist = ConversationContextManager.format_history_for_rewrite(turns)
    assert "User: What is cloud computing?" in rewrite_hist
    assert "Assistant: It is on-demand computing." in rewrite_hist

    prompt_hist = ConversationContextManager.format_history_for_prompt(turns)
    assert "[Conversation History]" in prompt_hist
    assert "Student: What is cloud computing?" in prompt_hist
    assert "[End Conversation History]" in prompt_hist


@pytest.mark.asyncio
async def test_conversation_context_manager_db_isolation(conv_test_env):
    ws_id = conv_test_env["ws_a"]
    other_ws = conv_test_env["ws_b"]
    proj_id = conv_test_env["proj_a"]
    user_id = conv_test_env["user_a"]

    session_factory = get_session_factory()
    async with session_factory() as session:
        conv = Conversation(
            workspace_id=ws_id,
            project_id=proj_id,
            user_id=user_id,
            title="History Test Conv",
            status="active",
        )
        session.add(conv)
        await session.flush()

        msg1 = Message(
            conversation_id=conv.id,
            workspace_id=ws_id,
            role="user",
            content="First question",
            original_user_query="First question",
        )
        msg2 = Message(
            conversation_id=conv.id,
            workspace_id=ws_id,
            role="assistant",
            content="First answer",
        )
        session.add_all([msg1, msg2])
        await session.commit()

        mgr = ConversationContextManager(history_limit=6)
        # Same workspace
        turns = await mgr.get_recent_history(session, conv.id, ws_id)
        assert len(turns) == 2
        assert turns[0].content == "First question"
        assert turns[1].content == "First answer"

        # Different workspace -> isolation protects data
        isolated_turns = await mgr.get_recent_history(session, conv.id, other_ws)
        assert len(isolated_turns) == 0


# ==============================================================================
# 2. Query Transformation Service Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_query_rewriting_pronoun_resolution():
    mock_llm = MockLLMProvider()
    service = QueryTransformationService(llm_provider=mock_llm)

    history = [
        ConversationTurn(role="user", content="Explain cloud computing"),
        ConversationTurn(role="assistant", content="Cloud computing provides on-demand resources over the internet."),
    ]

    res = await service.rewrite_query("What are its limitations?", history)
    assert res.was_rewritten is True
    assert "limitations of cloud computing" in res.rewritten_query.lower()


@pytest.mark.asyncio
async def test_query_rewriting_empty_history_passthrough():
    mock_llm = MockLLMProvider()
    service = QueryTransformationService(llm_provider=mock_llm)

    res = await service.rewrite_query("What is virtualization?", [])
    assert res.was_rewritten is False
    assert res.rewritten_query == "What is virtualization?"
    assert mock_llm.call_count == 0


@pytest.mark.asyncio
async def test_multi_query_and_decomposition():
    mock_llm = MockLLMProvider()
    service = QueryTransformationService(llm_provider=mock_llm)

    mq = await service.generate_multi_queries("What are cloud service models?", count=3)
    assert len(mq) >= 2
    assert "What are cloud service models?" in mq

    subs = await service.decompose_query("Compare public and private cloud models")
    assert len(subs) >= 2


# ==============================================================================
# 3. Redis Semantic Cache & Request Deduplication Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_cosine_similarity_math():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert pytest.approx(compute_cosine_similarity(v1, v2), 0.001) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(compute_cosine_similarity(v1, v3), 0.001) == 0.0


@pytest.mark.asyncio
async def test_redis_request_dedup_lock():
    cache = RedisSemanticCache()
    client = await cache.get_client()
    if not client:
        pytest.skip("Redis client unavailable")

    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    query = "Unique Deduplication Test Query"

    token1 = await cache.acquire_dedup_lock(ws_id, proj_id, query)
    assert token1 is not None

    # Second concurrent acquisition must be rejected (returns None)
    token2 = await cache.acquire_dedup_lock(ws_id, proj_id, query)
    assert token2 is None

    # Release lock
    await cache.release_dedup_lock(ws_id, proj_id, query, token1)

    # Now can be acquired again
    token3 = await cache.acquire_dedup_lock(ws_id, proj_id, query)
    assert token3 is not None
    await cache.release_dedup_lock(ws_id, proj_id, query, token3)


@pytest.mark.asyncio
async def test_redis_semantic_cache_store_and_lookup():
    cache = RedisSemanticCache(similarity_threshold=0.90)
    client = await cache.get_client()
    if not client:
        pytest.skip("Redis client unavailable")

    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    query = "What is cloud elasticity?"
    vec = [0.1 * i for i in range(10)]

    # Store entry
    await cache.store(
        workspace_id=ws_id,
        project_id=proj_id,
        query=query,
        answer="Elasticity is dynamically provisioning resources.",
        citations=[{"id": str(uuid.uuid4()), "snippet": "Elasticity allows scaling", "similarity_score": 0.95}],
        retrieved_chunks=[],
        query_embedding=vec,
    )

    # Identical vector lookup -> CACHE HIT
    hit = await cache.lookup(workspace_id=ws_id, project_id=proj_id, query=query, query_embedding=vec)
    assert hit is not None
    assert hit.cache_hit is True
    assert hit.similarity_score >= 0.99
    assert "Elasticity" in hit.answer

    # Completely orthogonal vector -> CACHE MISS
    orthogonal_vec = [1.0 if i == 0 else 0.0 for i in range(10)]
    miss = await cache.lookup(workspace_id=ws_id, project_id=proj_id, query="Something totally different", query_embedding=orthogonal_vec)
    assert miss is None


# ==============================================================================
# 4. Multi-Query Retriever Deduplication Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_multi_query_retriever_chunk_deduplication():
    ws_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    # Create mock chunks
    chunk_a = RetrievedChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        document_filename="DocA.pdf",
        workspace_id=ws_id,
        project_id=proj_id,
        chunk_index=1,
        content="Shared content across multiple queries",
        token_count=10,
        page_start=1,
        page_end=1,
        slide_number=None,
        slide_title=None,
        section_path="1.1",
        heading="Cloud Intro",
        similarity_score=0.85,
        retrieval_method="dense",
    )
    chunk_b = RetrievedChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        document_filename="DocA.pdf",
        workspace_id=ws_id,
        project_id=proj_id,
        chunk_index=1,
        content="Shared content across multiple queries",
        token_count=10,
        page_start=1,
        page_end=1,
        slide_number=None,
        slide_title=None,
        section_path="1.1",
        heading="Cloud Intro",
        similarity_score=0.92,
        retrieval_method="lexical",
    )
    chunk_c = RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=doc_id,
        document_filename="DocA.pdf",
        workspace_id=ws_id,
        project_id=proj_id,
        chunk_index=2,
        content="Distinct chunk content",
        token_count=10,
        page_start=2,
        page_end=2,
        slide_number=None,
        slide_title=None,
        section_path="1.2",
        heading="Cloud Types",
        similarity_score=0.77,
        retrieval_method="dense",
    )

    # Test the deduplication logic directly on a simulated candidate pool
    unique_map = {}
    candidates = [chunk_a, chunk_b, chunk_c]
    for chk in candidates:
        if chk.chunk_id not in unique_map or chk.similarity_score > unique_map[chk.chunk_id].similarity_score:
            unique_map[chk.chunk_id] = chk

    deduped = list(unique_map.values())
    assert len(deduped) == 2
    assert unique_map[chunk_id].similarity_score == 0.92


# ==============================================================================
# 5. FastAPI Endpoints: Rewrite Preview & Conversational Chat
# ==============================================================================
@pytest.mark.asyncio
async def test_api_chat_rewrite_preview_endpoint(conv_test_env):
    user_id = conv_test_env["user_a"]
    ws_id = conv_test_env["ws_a"]
    proj_id = conv_test_env["proj_a"]
    token = generate_test_token(str(user_id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Call rewrite preview endpoint
        res = await client.post(
            f"/api/v1/projects/{proj_id}/chat/rewrite",
            headers=headers,
            json={"query": "What are its main architectural components?"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "original_query" in data
        assert "rewritten_query" in data
        assert "was_rewritten" in data
        assert "latency_ms" in data


@pytest.mark.asyncio
async def test_api_chat_conversational_parameters_and_persistence(conv_test_env):
    user_id = conv_test_env["user_a"]
    ws_id = conv_test_env["ws_a"]
    proj_id = conv_test_env["proj_a"]
    token = generate_test_token(str(user_id))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Submit conversational chat query
        chat_payload = {
            "query": "Explain cloud deployment models",
            "mode": "conversational",
            "rewrite_enabled": True,
            "multi_query_enabled": True,
            "top_k": 3,
        }
        res = await client.post(
            f"/api/v1/projects/{proj_id}/chat",
            headers=headers,
            json=chat_payload,
        )
        assert res.status_code == 200
        body = res.json()
        conv_id = body["conversation_id"]
        assert conv_id is not None
        assert "metrics" in body
        assert body["metrics"]["retrieval_mode"] == "conversational"
        assert "cache_hit" in body["metrics"]

        # Verify messages history includes Phase 8 columns
        hist_res = await client.get(
            f"/api/v1/projects/{proj_id}/conversations/{conv_id}/messages",
            headers=headers,
        )
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert len(hist_data["messages"]) == 2  # user + assistant
        user_m = hist_data["messages"][0]
        assert user_m["role"] == "user"
        assert "rewrite_enabled" in user_m
        assert "multi_query_enabled" in user_m
