import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from app.core.auth import DEV_TEST_JWT_SECRET
from app.db.repository import store
from app.main import app


def create_test_token(user_id: str, email: str = "test@studyspace.ai") -> str:
    """Helper to generate a valid test JWT token."""
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "user_metadata": {"full_name": f"User {user_id[:6]}"}
    }
    return jwt.encode(payload, DEV_TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def clean_store():
    store.clear()
    yield
    store.clear()


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/me")
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "UNAUTHORIZED"
        assert "Authentication credentials are required" in data["error"]["message"]


@pytest.mark.asyncio
async def test_malformed_auth_header_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/me", headers={"Authorization": "NotBearerToken"})
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "MALFORMED_AUTHORIZATION_HEADER"


@pytest.mark.asyncio
async def test_authenticated_profile_resolution_and_provisioning():
    token = create_test_token(user_id="user-12345", email="student@university.edu")
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First request auto-provisions profile & workspace
        response = await client.get("/api/v1/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user-12345"
        assert data["email"] == "student@university.edu"
        assert data["workspace_id"] is not None
        assert data["workspace_name"] == "Personal Workspace"
        assert data["display_name"] == "User user-1"

        # Explicit provision updates display name without creating duplicate workspace
        prov_response = await client.post(
            "/api/v1/auth/provision",
            headers=headers,
            json={"display_name": "Alice Smith"}
        )
        assert prov_response.status_code == 200
        prov_data = prov_response.json()
        assert prov_data["display_name"] == "Alice Smith"
        assert prov_data["workspace_id"] == data["workspace_id"]
