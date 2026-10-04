import time
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.api_key_auth import _in_memory_rate_limit
from app.db.repository import store
from app.main import app
from tests.test_auth import create_test_token


from sqlalchemy import delete
from app.db.models import ApiKey, UsageEvent
from app.db.session import get_session_factory


@pytest.fixture(autouse=True)
async def clean_store():
    store.clear()
    _in_memory_rate_limit.clear()
    try:
        session_factory = get_session_factory()
        if session_factory:
            async with session_factory() as session:
                await session.execute(delete(UsageEvent))
                await session.execute(delete(ApiKey))
                await session.commit()
    except Exception:
        pass
    yield
    store.clear()
    _in_memory_rate_limit.clear()
    try:
        session_factory = get_session_factory()
        if session_factory:
            async with session_factory() as session:
                await session.execute(delete(UsageEvent))
                await session.execute(delete(ApiKey))
                await session.commit()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_api_key_lifecycle_and_masking():
    token = create_test_token("dev-user-01", "dev01@studyspace.ai")
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create API Key
        create_res = await client.post(
            "/api/v1/developer/keys",
            headers=auth_headers,
            json={
                "name": "Production Agent Key",
                "scopes": ["chat:write", "retrieval:read"],
                "expires_in_days": 30,
            },
        )
        assert create_res.status_code == 201
        created_data = create_res.json()

        key_id = created_data["id"]
        raw_api_key = created_data["api_key"]
        prefix = created_data["key_prefix"]

        # Assert secret starts with sk_live_
        assert raw_api_key.startswith("sk_live_")
        assert prefix.startswith("sk_live_")
        assert created_data["name"] == "Production Agent Key"
        assert created_data["status"] == "active"
        assert "chat:write" in created_data["scopes"]
        assert "retrieval:read" in created_data["scopes"]

        # 2. List API Keys (Secret key must NOT be revealed)
        list_res = await client.get("/api/v1/developer/keys", headers=auth_headers)
        assert list_res.status_code == 200
        keys_list = list_res.json()["keys"]
        assert len(keys_list) == 1

        listed_key = keys_list[0]
        assert listed_key["id"] == key_id
        assert "api_key" not in listed_key  # Secret masked
        assert listed_key["key_prefix"] == prefix

        # 3. Revoke API Key
        del_res = await client.delete(f"/api/v1/developer/keys/{key_id}", headers=auth_headers)
        assert del_res.status_code == 204

        # 4. Verify status is revoked
        list_res2 = await client.get("/api/v1/developer/keys", headers=auth_headers)
        assert list_res2.status_code == 200
        assert list_res2.json()["keys"][0]["status"] == "revoked"


@pytest.mark.asyncio
async def test_programmatic_api_access_and_authentication():
    token = create_test_token("dev-user-02", "dev02@studyspace.ai")
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        proj_res = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={"name": "Distributed Systems", "subject": "CS 450"},
        )
        project_id = proj_res.json()["id"]

        # Add revision item
        await client.post(
            f"/api/v1/projects/{project_id}/revision",
            headers=auth_headers,
            json={"title": "Raft Consensus Protocol", "status": "learning"},
        )

        # Create API key with all scopes
        key_res = await client.post(
            "/api/v1/developer/keys",
            headers=auth_headers,
            json={"name": "All Scopes Key", "scopes": ["chat:write", "retrieval:read", "revision:read"]},
        )
        raw_key = key_res.json()["api_key"]
        key_id = key_res.json()["id"]

        # 1. Access using X-API-Key header
        chat_res = await client.post(
            "/api/v1/dev/chat",
            headers={"X-API-Key": raw_key},
            json={"project_id": project_id, "message": "Explain leader election in Raft"},
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert chat_data["project_id"] == project_id
        assert len(chat_data["reply"]) > 0

        # 2. Access using Authorization: Bearer sk_live_...
        ret_res = await client.post(
            "/api/v1/dev/retrieve",
            headers={"Authorization": f"Bearer {raw_key}"},
            json={"project_id": project_id, "query": "Raft", "top_k": 3},
        )
        assert ret_res.status_code == 200

        # 3. Access revision item via developer programmatic route
        rev_res = await client.get(
            f"/api/v1/dev/projects/{project_id}/revision",
            headers={"X-API-Key": raw_key},
        )
        assert rev_res.status_code == 200
        rev_data = rev_res.json()
        assert len(rev_data["items"]) == 1
        assert rev_data["items"][0]["title"] == "Raft Consensus Protocol"

        # 4. Attempt access with invalid key
        bad_res = await client.post(
            "/api/v1/dev/chat",
            headers={"X-API-Key": "sk_live_bogus_key_1234567890abcdef"},
            json={"project_id": project_id, "message": "Hello"},
        )
        assert bad_res.status_code == 401

        # 5. Attempt access with malformed key (no prefix)
        malformed_res = await client.post(
            "/api/v1/dev/chat",
            headers={"X-API-Key": "invalid_prefix_key"},
            json={"project_id": project_id, "message": "Hello"},
        )
        assert malformed_res.status_code == 401

        # 6. Revoke key and attempt access
        await client.delete(f"/api/v1/developer/keys/{key_id}", headers=auth_headers)
        revoked_res = await client.post(
            "/api/v1/dev/chat",
            headers={"X-API-Key": raw_key},
            json={"project_id": project_id, "message": "Hello"},
        )
        assert revoked_res.status_code == 401


@pytest.mark.asyncio
async def test_scope_enforcement():
    token = create_test_token("dev-user-03", "dev03@studyspace.ai")
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create key with ONLY 'retrieval:read' scope
        key_res = await client.post(
            "/api/v1/developer/keys",
            headers=auth_headers,
            json={"name": "Retrieval Only Key", "scopes": ["retrieval:read"]},
        )
        raw_key = key_res.json()["api_key"]

        # Call retrieval endpoint -> 200 OK
        ret_res = await client.post(
            "/api/v1/dev/retrieve",
            headers={"X-API-Key": raw_key},
            json={"project_id": "proj-1", "query": "Consensus", "top_k": 2},
        )
        assert ret_res.status_code == 200

        # Call chat endpoint (requires chat:write) -> 403 Forbidden
        chat_res = await client.post(
            "/api/v1/dev/chat",
            headers={"X-API-Key": raw_key},
            json={"project_id": "proj-1", "message": "Hello"},
        )
        assert chat_res.status_code == 403
        assert "Insufficient permissions" in chat_res.json()["detail"]


@pytest.mark.asyncio
async def test_rate_limiting_and_usage_logging():
    token = create_test_token("dev-user-04", "dev04@studyspace.ai")
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        key_res = await client.post(
            "/api/v1/developer/keys",
            headers=auth_headers,
            json={"name": "Rate Limited Key", "scopes": ["retrieval:read"]},
        )
        raw_key = key_res.json()["api_key"]
        key_id = key_res.json()["id"]

        # Simulate 100 requests already consumed in this minute window
        now = time.time()
        _in_memory_rate_limit[key_id] = [now for _ in range(100)]

        # 101st request should be rejected with 429
        rate_res = await client.post(
            "/api/v1/dev/retrieve",
            headers={"X-API-Key": raw_key},
            json={"project_id": "proj-1", "query": "Rate check"},
        )
        assert rate_res.status_code == 429
        assert "Retry-After" in rate_res.headers
        assert rate_res.headers["Retry-After"] == "60"

        # Clear rate limit and execute 1 successful request to record usage
        _in_memory_rate_limit[key_id] = []
        ok_res = await client.post(
            "/api/v1/dev/retrieve",
            headers={"X-API-Key": raw_key},
            json={"project_id": "proj-1", "query": "Valid query"},
        )
        assert ok_res.status_code == 200

        # Check usage summary endpoint
        usage_res = await client.get("/api/v1/developer/usage", headers=auth_headers)
        assert usage_res.status_code == 200
        usage_data = usage_res.json()
        assert usage_data["total_requests"] >= 1
        assert len(usage_data["recent_events"]) >= 1
        assert usage_data["recent_events"][0]["event_type"] == "retrieval"
